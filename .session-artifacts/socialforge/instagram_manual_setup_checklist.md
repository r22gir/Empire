# Instagram Manual Setup Checklist — Empire Workroom

## Step 1: Create Account
- [ ] Go to instagram.com or open Instagram app
- [ ] Sign up with email: empirebox2026@gmail.com
- [ ] Username: @empire_workroom (alternatives: @empireworkroom, @empire.workroom)
- [ ] Full name: Empire Workroom
- [ ] Set profile photo (Empire logo)

## Step 2: Switch to Business Account
- [ ] Settings > Account > Switch to Professional Account
- [ ] Select: Business (NOT Creator)
- [ ] Category: Interior Designer or Home Decor
- [ ] Add contact: (703) 213-6484, workroom@empirebox.store
- [ ] Add address: 5124 Frolich Ln, Hyattsville, MD 20781

## Step 3: Set Bio
- [ ] Bio: Custom Window Treatments & Upholstery | AI-Powered Design | DC - MD - VA
- [ ] Website: studio.empirebox.store
- [ ] Action button: Contact or Book Now

## Step 4: Link to Facebook Page
- [ ] During Business setup, select "Empire Workroom" Facebook Page
- [ ] OR: Instagram Settings > Account > Linked Accounts > Facebook > Empire Workroom

## Step 5: Verify Connection
Run on EmpireDell terminal:
```
TOKEN=$(grep META_ACCESS_TOKEN ~/empire-repo/backend/.env | cut -d= -f2)
curl -s "https://graph.facebook.com/v19.0/1013347598533893?fields=instagram_business_account&access_token=$TOKEN" | python3 -m json.tool
```
Should return: {"instagram_business_account": {"id": "SOME_NUMBER"}}

## Step 6: Add to .env
Add to ~/empire-repo/backend/.env:
INSTAGRAM_BUSINESS_ID=SOME_NUMBER

## Step 7: Restart Backend
sudo systemctl restart empire-backend

## Step 8: Test
Tell MAX: "publish test post to Instagram"

## WoodCraft (Later)
Repeat with @empirewoodcraft, create WoodCraft FB Page first, then link.
