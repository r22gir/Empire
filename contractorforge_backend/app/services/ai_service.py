"""
AI Service for conversational project intake
Uses OpenAI GPT-4 for natural language understanding
"""
from typing import Dict, List, Any, Optional
import json
from app.config import settings
from app.templates import get_template


try:
    from openai import OpenAI
    client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
except ImportError:
    client = None


class AIService:
    """
    Service for AI-powered conversation and data extraction
    """
    
    def __init__(self):
        self.client = client
    
    def start_conversation(self, industry_code: str) -> Dict[str, Any]:
        """
        Start a new conversation for project intake
        """
        template = get_template(industry_code)
        greeting = template.ai_intake_prompts.get("greeting", "Hello! How can I help you today?")
        
        return {
            "message": greeting,
            "conversation_id": None,  # Will be set when saving to DB
            "industry": industry_code,
            "extracted_data": {},
            "is_complete": False,
        }
    
    async def process_message(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        industry_code: str,
        extracted_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a user message and generate AI response
        
        Args:
            user_message: User's message
            conversation_history: Previous messages
            industry_code: Industry template code
            extracted_data: Previously extracted data
        
        Returns:
            Dict with AI response and updated extracted data
        """
        if not self.client:
            return self._fallback_response(user_message, industry_code)
        
        template = get_template(industry_code)
        extracted_data = extracted_data or {}
        
        # Build system prompt
        system_prompt = self._build_system_prompt(template, extracted_data)
        
        # Build messages for OpenAI
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        for msg in conversation_history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        try:
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.7,
                max_tokens=500,
            )
            
            assistant_message = response.choices[0].message.content
            
            # Extract structured data from conversation
            updated_data = await self._extract_data(
                user_message,
                assistant_message,
                extracted_data,
                industry_code
            )
            
            # Check if we have enough information to generate estimate
            is_complete = self._check_completion(updated_data, template)
            
            return {
                "message": assistant_message,
                "extracted_data": updated_data,
                "is_complete": is_complete,
                "can_generate_estimate": is_complete,
            }
        
        except Exception as e:
            return {
                "message": f"I apologize, but I'm having trouble processing your message right now. Error: {str(e)}",
                "extracted_data": extracted_data,
                "is_complete": False,
                "error": str(e),
            }
    
    def _build_system_prompt(
        self,
        template,
        extracted_data: Dict[str, Any]
    ) -> str:
        """Build system prompt for OpenAI"""
        
        prompt = f"""You are an AI assistant helping to collect information for a {template.industry_name} project.

Your goal is to gather the following information through natural conversation:
"""
        
        # Add industry-specific information needs
        if template.industry_code == "workroom":
            prompt += """
- Number and type of window treatments needed
- Window measurements (width and height for each)
- Fabric preferences (provided by customer or need to source)
- Hardware requirements
- Installation needs
- Timeline

Ask questions naturally, one or two at a time. Be friendly and helpful.
"""
        elif template.industry_code == "electrician":
            prompt += """
- Type of electrical work needed
- Urgency level (emergency or standard)
- Specific fixtures or installations
- Location (residential/commercial, indoor/outdoor)
- Timeline
- Permit requirements

Ask questions naturally, one or two at a time. Be professional and safety-focused.
"""
        elif template.industry_code == "landscaping":
            prompt += """
- Type of landscaping work (installation, renovation, design)
- Areas to be landscaped and approximate sizes
- Plant preferences
- Hardscaping needs (patio, walkway, etc.)
- Timeline and seasonal considerations
- Budget range

Ask questions naturally, one or two at a time. Be enthusiastic about creating beautiful outdoor spaces.
"""
        
        if extracted_data:
            prompt += f"\n\nInformation collected so far:\n{json.dumps(extracted_data, indent=2)}"
        
        prompt += "\n\nRemember: Keep responses concise and friendly. Guide the conversation naturally."
        
        return prompt
    
    async def _extract_data(
        self,
        user_message: str,
        assistant_message: str,
        current_data: Dict[str, Any],
        industry_code: str
    ) -> Dict[str, Any]:
        """
        Extract structured data from conversation
        Uses simple pattern matching and NLU
        """
        updated_data = current_data.copy()
        
        # Simple extraction patterns
        # In production, would use more sophisticated NLU
        
        # Extract numbers
        import re
        numbers = re.findall(r'\d+', user_message)
        
        # Common patterns
        if any(word in user_message.lower() for word in ["window", "windows"]):
            if "window_count" not in updated_data and numbers:
                updated_data["window_count"] = int(numbers[0])
        
        if any(word in user_message.lower() for word in ["emergency", "urgent"]):
            updated_data["is_emergency"] = True
        
        if any(word in user_message.lower() for word in ["width", "wide"]):
            if numbers:
                if "measurements" not in updated_data:
                    updated_data["measurements"] = {}
                if "width" not in updated_data["measurements"]:
                    updated_data["measurements"]["width"] = int(numbers[0])
        
        if any(word in user_message.lower() for word in ["height", "tall"]):
            if numbers:
                if "measurements" not in updated_data:
                    updated_data["measurements"] = {}
                if "height" not in updated_data["measurements"]:
                    updated_data["measurements"]["height"] = int(numbers[0])
        
        # Extract timeline
        if any(word in user_message.lower() for word in ["week", "weeks", "month", "months"]):
            updated_data["timeline_mentioned"] = True
        
        return updated_data
    
    def _check_completion(
        self,
        extracted_data: Dict[str, Any],
        template
    ) -> bool:
        """
        Check if we have enough information to generate estimate
        """
        # Basic check - can be made more sophisticated
        
        if template.industry_code == "workroom":
            has_windows = "window_count" in extracted_data or "measurements" in extracted_data
            return has_windows
        
        elif template.industry_code == "electrician":
            has_work_type = "work_type" in extracted_data or len(extracted_data) > 2
            return has_work_type
        
        elif template.industry_code == "landscaping":
            has_scope = "project_type" in extracted_data or len(extracted_data) > 2
            return has_scope
        
        return False
    
    def _fallback_response(self, user_message: str, industry_code: str) -> Dict[str, Any]:
        """
        Fallback response when OpenAI is not available
        """
        template = get_template(industry_code)
        
        return {
            "message": "Thank you for that information. Could you tell me more about your project?",
            "extracted_data": {},
            "is_complete": False,
            "note": "OpenAI integration not configured - using fallback responses",
        }
    
    def generate_estimate_summary(
        self,
        extracted_data: Dict[str, Any],
        estimate_data: Dict[str, Any],
        industry_code: str
    ) -> str:
        """
        Generate a human-readable summary of the estimate
        """
        template = get_template(industry_code)
        
        summary = f"Based on your {template.industry_name} project, here's your estimate:\n\n"
        
        for item in estimate_data.get("line_items", []):
            summary += f"• {item['description']}: ${item['amount']:.2f}\n"
        
        summary += f"\nSubtotal: ${estimate_data['subtotal']:.2f}\n"
        summary += f"Tax: ${estimate_data['tax_amount']:.2f}\n"
        summary += f"**Total: ${estimate_data['total']:.2f}**\n\n"
        
        if estimate_data.get("deposit_amount", 0) > 0:
            summary += f"Deposit Required: ${estimate_data['deposit_amount']:.2f} ({estimate_data['deposit_percentage']}%)\n"
            summary += f"Balance Due: ${estimate_data['balance_due']:.2f}\n"
        
        return summary


# Singleton service
ai_service = AIService()
