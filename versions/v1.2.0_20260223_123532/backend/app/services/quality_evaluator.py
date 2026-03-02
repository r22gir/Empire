"""
Quality Evaluator service for LLM-based assessment of listings, estimates, and work quality.
"""
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.services.economic_service import EconomicService
import uuid


class QualityEvaluator:
    """
    Service for AI-powered quality evaluation of content.
    
    Provides LLM-based scoring and feedback for:
    - Product listings
    - Descriptions
    - Pricing accuracy
    - Overall quality assessment
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def evaluate_listing(
        self,
        listing_data: Dict[str, Any],
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate quality of a product listing.
        
        Args:
            listing_data: Dictionary with listing details (title, description, price, etc.)
            category: Optional category for category-specific rubrics
            
        Returns:
            Dictionary with quality scores and feedback
        """
        if not settings.quality_eval_enabled:
            return {
                "overall_score": 100.0,
                "accuracy_score": 100.0,
                "completeness_score": 100.0,
                "professionalism_score": 100.0,
                "feedback": "Quality evaluation disabled",
                "suggestions": []
            }
        
        # TODO: Implement actual LLM evaluation
        # This would use GPT-4 or similar to evaluate the listing
        # For now, use heuristic-based evaluation
        
        scores = await self._heuristic_evaluation(listing_data, category)
        
        # Track the evaluation cost
        if settings.economic_enabled:
            economic_service = EconomicService(self.db)
            # Estimate tokens used for evaluation (would be actual in real implementation)
            input_tokens = len(str(listing_data)) * 2  # Rough estimate
            output_tokens = 200  # Typical evaluation response
            
            await economic_service.record_ai_cost(
                entity_type="user",
                entity_id=listing_data.get("user_id", uuid.uuid4()),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model=settings.quality_eval_model,
                description="Quality evaluation of listing"
            )
        
        return scores
    
    async def _heuristic_evaluation(
        self,
        listing_data: Dict[str, Any],
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Perform heuristic-based quality evaluation.
        
        This is a fallback method that uses rules instead of LLM.
        In production, this would be replaced with actual LLM evaluation.
        
        Args:
            listing_data: Listing data to evaluate
            category: Optional category
            
        Returns:
            Quality scores and feedback
        """
        title = listing_data.get("title", "")
        description = listing_data.get("description", "")
        price = listing_data.get("price", 0)
        photos = listing_data.get("photos", [])
        
        # Accuracy Score (0-100): Based on completeness of information
        accuracy_score = 50.0  # Base score
        
        if price > 0:
            accuracy_score += 20.0
        
        if len(photos) > 0:
            accuracy_score += 15.0
        
        if category:
            accuracy_score += 15.0
        
        # Completeness Score (0-100): Based on field presence and quality
        completeness_score = 0.0
        
        if title and len(title) >= 10:
            completeness_score += 25.0
        elif title:
            completeness_score += 10.0
        
        if description and len(description) >= 50:
            completeness_score += 30.0
        elif description:
            completeness_score += 15.0
        
        if price > 0:
            completeness_score += 20.0
        
        if len(photos) >= 3:
            completeness_score += 25.0
        elif len(photos) > 0:
            completeness_score += 10.0
        
        # Professionalism Score (0-100): Based on formatting and clarity
        professionalism_score = 60.0  # Base score
        
        # Check for proper capitalization in title
        if title and title[0].isupper():
            professionalism_score += 10.0
        
        # Check description quality
        if description:
            if len(description) >= 100:
                professionalism_score += 15.0
            if "." in description:  # Has sentences
                professionalism_score += 15.0
        
        # Cap scores at 100
        accuracy_score = min(accuracy_score, 100.0)
        completeness_score = min(completeness_score, 100.0)
        professionalism_score = min(professionalism_score, 100.0)
        
        # Calculate weighted overall score
        # 40% accuracy, 30% completeness, 30% professionalism
        overall_score = (
            accuracy_score * 0.40 +
            completeness_score * 0.30 +
            professionalism_score * 0.30
        )
        
        # Generate feedback and suggestions
        feedback_items = []
        suggestions = []
        
        if accuracy_score < 70:
            feedback_items.append("Accuracy could be improved with more details")
            suggestions.append("Add category and more photos")
        
        if completeness_score < 70:
            feedback_items.append("Some required information is missing")
            if not description or len(description) < 50:
                suggestions.append("Add a detailed description (at least 50 characters)")
            if len(photos) < 3:
                suggestions.append("Add more photos (aim for 3-5 images)")
        
        if professionalism_score < 70:
            feedback_items.append("Presentation could be more professional")
            if not title or not title[0].isupper():
                suggestions.append("Capitalize the first letter of the title")
            if not description or len(description) < 100:
                suggestions.append("Write a more detailed description (100+ characters)")
        
        if overall_score >= 90:
            feedback_items = ["Excellent quality! This listing is well-optimized."]
        elif overall_score >= 80:
            feedback_items.insert(0, "Good quality overall with minor improvements possible.")
        elif overall_score >= 70:
            feedback_items.insert(0, "Decent quality but could use some improvements.")
        else:
            feedback_items.insert(0, "This listing needs significant improvements.")
        
        return {
            "overall_score": round(overall_score, 2),
            "accuracy_score": round(accuracy_score, 2),
            "completeness_score": round(completeness_score, 2),
            "professionalism_score": round(professionalism_score, 2),
            "feedback": " ".join(feedback_items),
            "suggestions": suggestions,
            "evaluation_method": "heuristic",  # Would be "llm" in production
        }
    
    async def generate_llm_evaluation_prompt(
        self,
        listing_data: Dict[str, Any],
        category: Optional[str] = None
    ) -> str:
        """
        Generate LLM prompt for quality evaluation.
        
        This prompt would be sent to GPT-4 for actual evaluation.
        
        Args:
            listing_data: Listing data to evaluate
            category: Optional category
            
        Returns:
            Formatted prompt string
        """
        category_context = ""
        if category:
            category_context = f"\nCategory: {category}\n"
            
            # Add category-specific rubrics
            if category.lower() in ["electronics", "technology"]:
                category_context += """
Category-specific considerations:
- Technical specifications should be detailed
- Condition of electronic components is critical
- Include model numbers and compatibility information
"""
            elif category.lower() in ["clothing", "fashion"]:
                category_context += """
Category-specific considerations:
- Size information must be clear and accurate
- Material and care instructions should be provided
- Condition should address any wear, stains, or damage
"""
            elif category.lower() in ["furniture", "home"]:
                category_context += """
Category-specific considerations:
- Dimensions are critical for buyers
- Material and construction quality should be detailed
- Assembly requirements should be mentioned
"""
        
        prompt = f"""
You are a quality evaluation expert for online product listings. Evaluate the following listing and provide scores.

Listing Information:
{category_context}
Title: {listing_data.get('title', 'N/A')}
Description: {listing_data.get('description', 'N/A')}
Price: ${listing_data.get('price', 0)}
Photos: {len(listing_data.get('photos', []))} images
Condition: {listing_data.get('condition', 'N/A')}

Evaluation Criteria:

1. ACCURACY (0-100): How accurate and appropriate is the pricing and product information?
   - Pricing seems reasonable for the item
   - Product details are factually correct
   - Condition assessment is honest

2. COMPLETENESS (0-100): Are all required fields present and sufficiently detailed?
   - Title is descriptive and complete
   - Description provides all necessary information
   - Adequate number of photos
   - Key specifications included

3. PROFESSIONALISM (0-100): How professional and well-formatted is the listing?
   - Proper grammar and spelling
   - Clear and organized formatting
   - Professional tone
   - No inappropriate content

Please provide:
1. Overall Score (weighted average: 40% accuracy, 30% completeness, 30% professionalism)
2. Individual scores for Accuracy, Completeness, and Professionalism
3. Brief feedback summary (2-3 sentences)
4. 2-3 specific suggestions for improvement

Format your response as JSON:
{{
    "overall_score": float,
    "accuracy_score": float,
    "completeness_score": float,
    "professionalism_score": float,
    "feedback": "string",
    "suggestions": ["string", "string"]
}}
"""
        return prompt.strip()
    
    async def batch_evaluate_listings(
        self,
        listings: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Evaluate multiple listings in batch.
        
        Args:
            listings: List of listing data dictionaries
            
        Returns:
            List of evaluation results
        """
        results = []
        for listing in listings:
            evaluation = await self.evaluate_listing(
                listing_data=listing,
                category=listing.get("category")
            )
            results.append({
                "listing_id": listing.get("id"),
                "evaluation": evaluation
            })
        
        return results
