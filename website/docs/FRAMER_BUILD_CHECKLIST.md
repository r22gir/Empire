# Framer Build Checklist for EmpireBox Website

This checklist guides you through building the EmpireBox marketing website in Framer from scratch.

## Pre-Build Setup

- [ ] Create new Framer project
- [ ] Name project "EmpireBox Website"
- [ ] Set canvas to responsive (Desktop 1440px, Tablet 768px, Mobile 375px)
- [ ] Import fonts: Montserrat (headings) and Inter (body)

## 1. Set Up Brand Colors

- [ ] Create color styles in Framer:
  - [ ] Primary Blue: `#0066FF`
  - [ ] Primary Dark: `#0052CC`
  - [ ] Secondary Orange: `#FF6600`
  - [ ] Secondary Dark: `#E55A00`
  - [ ] Dark: `#1A1A1A`
  - [ ] Light: `#F9F9F9`
  - [ ] White: `#FFFFFF`
  - [ ] Gray: `#666666`

## 2. Set Up Typography Styles

- [ ] Create text styles:
  - [ ] H1: Montserrat Bold, 72px (desktop), 48px (mobile)
  - [ ] H2: Montserrat Bold, 48px (desktop), 36px (mobile)
  - [ ] H3: Montserrat Semibold, 32px (desktop), 24px (mobile)
  - [ ] Body Large: Inter Regular, 18px
  - [ ] Body: Inter Regular, 16px
  - [ ] Small: Inter Regular, 14px

## 3. Build Navigation Component

- [ ] Create component "Navbar"
- [ ] Add logo: "⬛ EmpireBox" (text)
- [ ] Add navigation links: Home, Features, Pricing, FAQ, Contact
- [ ] Make sticky (position: fixed, top: 0)
- [ ] Add white background with drop shadow
- [ ] Create mobile variant with hamburger menu
- [ ] Add hover states to links (color change to Primary Blue)
- [ ] Set z-index to 1000

## 4. Build Hero Section

- [ ] Create new frame "Hero"
- [ ] Apply blue gradient background (Primary → Primary Dark, 135deg)
- [ ] Add H1: "The Operating System for Resellers"
- [ ] Add subtitle (Body Large): "From side hustle to $10K/month..."
- [ ] Create CTA button component:
  - [ ] Text: "Try Free for 7 Days"
  - [ ] Background: Secondary Orange
  - [ ] Padding: 16px 40px
  - [ ] Border radius: 50px
  - [ ] Add hover effect (lift + shadow)
- [ ] Center all content
- [ ] Set padding: 96px 0 (desktop), 64px 0 (mobile)

## 5. Build Features Section

- [ ] Create frame "Features"
- [ ] Add section title (H2): "Why Resellers Choose EmpireBox"
- [ ] Create 3-column grid (desktop), 1-column (mobile)
- [ ] Build feature card component:
  - [ ] White background
  - [ ] Border radius: 12px
  - [ ] Box shadow
  - [ ] Padding: 32px
  - [ ] Add hover effect (lift + larger shadow)

### Feature Card 1: MarketForge
- [ ] Add icon: 📸 (48px)
- [ ] Add title (H3): "MarketForge"
- [ ] Add subtitle: "Photo → Price → Post in 30 seconds"
- [ ] Add bullet list with checkmarks:
  - [ ] AI-powered pricing
  - [ ] Auto-description generation
  - [ ] Multi-platform posting
  - [ ] Instant crosslisting

### Feature Card 2: MarketF
- [ ] Add icon: 🏪
- [ ] Add title: "MarketF Marketplace"
- [ ] Add subtitle: "Your own marketplace with 8% fees"
- [ ] Add bullet list (4 features)

### Feature Card 3: AI Agents
- [ ] Add icon: 🤖
- [ ] Add title: "AI Agents"
- [ ] Add subtitle: "Work while you sleep, 24/7 automation"
- [ ] Add bullet list (4 features)

## 6. Build Testimonials Section

- [ ] Create frame "Testimonials"
- [ ] Add light gray background
- [ ] Add section title: "What Resellers Are Saying"
- [ ] Create 4-column grid (desktop), 2-column (tablet), 1-column (mobile)

### Build Testimonial Card Component
- [ ] White background
- [ ] Left border: 4px solid Primary Blue
- [ ] Border radius: 12px
- [ ] Padding: 24px
- [ ] Add 5 stars (⭐⭐⭐⭐⭐) in Secondary Orange
- [ ] Add quote text (italic)
- [ ] Add author name (bold, Primary Blue)
- [ ] Add author role (small text, gray)

### Add 4 Testimonials
- [ ] Sarah M. testimonial
- [ ] Mike T. testimonial
- [ ] Jessica L. testimonial
- [ ] David R. testimonial

### Stats Bar
- [ ] Create stats bar below testimonials
- [ ] Blue gradient background
- [ ] White text
- [ ] Text: "95% Retention | 72 NPS | $3.5K/month MRR"
- [ ] Center aligned
- [ ] Padding: 32px
- [ ] Border radius: 12px

## 7. Build How It Works Section

- [ ] Create frame "How It Works"
- [ ] Add section title: "How It Works"
- [ ] Create 3-column grid

### Build Step Component (reuse for all 3)
- [ ] Circle with number (60px diameter, Primary Blue background)
- [ ] White number text (24px)
- [ ] Step title (H3)
- [ ] Step description (Body)
- [ ] Center aligned

### Add 3 Steps
- [ ] Step 1: Upload Photo
- [ ] Step 2: Set Price
- [ ] Step 3: Get Paid

## 8. Build Pricing Section

- [ ] Create frame "Pricing"
- [ ] Add section title: "Simple, Transparent Pricing"
- [ ] Create 4-column grid (desktop), 2-column (tablet), 1-column (mobile)

### Build Pricing Card Component
- [ ] White background
- [ ] Box shadow
- [ ] Border radius: 12px
- [ ] Padding: 40px
- [ ] Center aligned
- [ ] Add hover effect

### Premium Card (Featured)
- [ ] Add orange border (4px)
- [ ] Scale up slightly (1.05)
- [ ] "Most Popular" badge

### Add 4 Pricing Tiers
- [ ] Free Trial ($0 / 7 Days)
- [ ] Pay-Per-Sale (3% Per Sale)
- [ ] Premium ($9.99/month) - FEATURED
- [ ] Hybrid ($5.99 + 1.5%)

### For Each Card
- [ ] Plan name (H3)
- [ ] Price (large, bold, Primary Blue)
- [ ] Period text (gray)
- [ ] Feature list with checkmarks
- [ ] CTA button

## 9. Build FAQ Section

- [ ] Create frame "FAQ"
- [ ] Add section title: "Frequently Asked Questions"
- [ ] Max width: 800px, centered

### Build FAQ Item Component (Accordion)
- [ ] Container with light gray background
- [ ] Question button (full width)
- [ ] Plus/minus icon (toggle on click)
- [ ] Hidden answer (slides down on click)
- [ ] Add click interaction: toggle answer visibility
- [ ] Border radius: 8px
- [ ] Margin between items: 16px

### Add 6 FAQ Items
- [ ] Is there a setup fee?
- [ ] How do I get paid?
- [ ] Can I cancel anytime?
- [ ] Which platforms are supported?
- [ ] Is my data safe?
- [ ] Is there a mobile app?

### Add Interactions
- [ ] Click to expand/collapse
- [ ] Rotate plus icon to X when expanded
- [ ] Smooth transition (0.3s ease)

## 10. Build CTA Section

- [ ] Create frame "CTA"
- [ ] Blue gradient background
- [ ] White text
- [ ] Center aligned
- [ ] Padding: 80px 0

### CTA Content
- [ ] Headline (H2): "Ready to Stop Wasting Time?"
- [ ] Subheadline: "Join 50+ resellers already making more..."
- [ ] Email form:
  - [ ] Email input field (white background, rounded)
  - [ ] Submit button (Secondary Orange)
  - [ ] Arrange horizontally (stack on mobile)
- [ ] Small text below: "No credit card required • 7-day free trial"

### Email Form Component
- [ ] Create form layout
- [ ] Email input (flex: 1)
- [ ] Submit button (fixed width)
- [ ] Add form submission interaction (show success message)

## 11. Build Footer

- [ ] Create frame "Footer"
- [ ] Dark background (#1A1A1A)
- [ ] White text
- [ ] Padding: 64px 0 24px

### Footer Content Grid (4 columns)
- [ ] Column 1: Brand
  - [ ] Logo/Name
  - [ ] Tagline
- [ ] Column 2: Quick Links
  - [ ] Home, Features, Pricing, FAQ
- [ ] Column 3: Legal
  - [ ] Privacy, Terms, Refund
- [ ] Column 4: Contact
  - [ ] Email: hello@empirebox.com
  - [ ] Support: 24/7

### Footer Bottom
- [ ] Divider line (1px, white 10% opacity)
- [ ] Copyright text (center): "© 2026 EmpireBox. All rights reserved."

## 12. Add Animations & Interactions

### Scroll Animations
- [ ] Hero elements: Fade in + slide up
- [ ] Feature cards: Fade in on scroll (stagger)
- [ ] Testimonials: Fade in on scroll
- [ ] Pricing cards: Fade in + scale
- [ ] FAQ items: Fade in on scroll

### Hover Effects
- [ ] Buttons: Lift + shadow
- [ ] Cards: Lift + shadow
- [ ] Links: Color change

### Click Interactions
- [ ] Navigation links: Smooth scroll to section
- [ ] CTA buttons: Link to email form
- [ ] Mobile menu: Toggle open/close
- [ ] FAQ items: Expand/collapse

## 13. Mobile Responsiveness

### For Each Section
- [ ] Test on mobile breakpoint (375px)
- [ ] Adjust font sizes (use responsive variants)
- [ ] Stack columns vertically
- [ ] Adjust padding/spacing
- [ ] Test mobile menu
- [ ] Ensure touch targets are 44x44px minimum

### Specific Mobile Adjustments
- [ ] Hero: Stack content, smaller text
- [ ] Features: Single column
- [ ] Testimonials: Single column
- [ ] Pricing: Single column
- [ ] Email form: Stack vertically
- [ ] Footer: Stack columns

## 14. Final Polish

### Visual QA
- [ ] Check alignment of all elements
- [ ] Verify consistent spacing (use 8px grid)
- [ ] Check font sizes and weights
- [ ] Verify color usage matches brand
- [ ] Check all shadows are consistent
- [ ] Verify border radius consistency

### Interaction QA
- [ ] Test all button clicks
- [ ] Test form submission
- [ ] Test FAQ accordion
- [ ] Test mobile menu
- [ ] Test smooth scrolling
- [ ] Test hover states

### Performance
- [ ] Optimize images (< 100KB each)
- [ ] Remove unused components
- [ ] Check page load speed
- [ ] Test on 3G connection

### Accessibility
- [ ] Add alt text to all images
- [ ] Ensure proper heading hierarchy
- [ ] Check color contrast (4.5:1 minimum)
- [ ] Test keyboard navigation
- [ ] Add focus indicators

## 15. Pre-Launch Checklist

- [ ] Spell check all copy
- [ ] Verify all links work
- [ ] Test email form (use test email)
- [ ] Preview in Framer (all breakpoints)
- [ ] Share preview link for feedback
- [ ] Export assets if needed
- [ ] Set up custom domain (if ready)
- [ ] Add favicon
- [ ] Set meta tags for SEO
- [ ] Add Open Graph tags
- [ ] Set up analytics (Google Analytics)

## 16. Launch

- [ ] Publish to Framer hosting
- [ ] Test live site on multiple devices
- [ ] Test on multiple browsers
- [ ] Monitor analytics
- [ ] Set up email capture backend
- [ ] Announce launch!

## Post-Launch

- [ ] Monitor form submissions
- [ ] Track analytics (views, conversions)
- [ ] Gather user feedback
- [ ] Plan first A/B tests
- [ ] Create content calendar for updates

---

**Tips for Building in Framer:**
- Use components for repeated elements (buttons, cards)
- Create variants for responsive designs
- Use Auto Layout for flexible layouts
- Test interactions in Preview mode frequently
- Save backups/versions regularly
- Get feedback before finalizing
