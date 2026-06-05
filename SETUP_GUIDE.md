# IBM Portfolio — Complete Setup Guide
## Three tasks to complete before submitting applications

---

## TASK 1 — Ruby on Rails CRUD App (3–4 days)
**Why:** AI Driven Skills Growth Developer lists Ruby on Rails as required.
**Goal:** One small working Rails app on GitHub.

### Step 1: Install Ruby and Rails
```bash
# Mac (use rbenv)
brew install rbenv ruby-build
rbenv install 3.2.0
rbenv global 3.2.0
gem install rails

# Windows: use WSL2 + Ubuntu, then same commands above
# Verify
ruby --version   # should show 3.2.x
rails --version  # should show 7.x
```

### Step 2: Create the app (follow official tutorial exactly)
Go to: https://guides.rubyonrails.org/getting_started.html

Build the "Blog" app from the tutorial. It teaches:
- MVC architecture (Model, View, Controller)
- ActiveRecord (Rails ORM for database)
- Routes and REST conventions
- Forms and CRUD operations

This takes 3–4 hours if you follow it carefully.

### Step 3: Extend it slightly to make it your own
Once the blog tutorial works, add one small feature:
```bash
# Add a "category" field to articles
rails generate migration AddCategoryToArticles category:string
rails db:migrate
```
Then show category in the index view. This small addition shows you understood the tutorial, not just copy-pasted it.

### Step 4: Push to GitHub
```bash
git init
git add .
git commit -m "Rails blog app — CRUD with categories"
git remote add origin https://github.com/[YOUR_GITHUB]/rails-blog-demo
git push -u origin main
```

### Step 5: Write a README
```markdown
# Rails Blog Demo
A CRUD blog application built with Ruby on Rails 7.

Built to learn Rails MVC architecture, ActiveRecord ORM,
RESTful routing, and form handling — as part of preparing
for full-stack development work on IBM's AI Productivity
Engineering team.

## Stack
- Ruby 3.2 · Rails 7 · SQLite (dev) · ERB templates

## Run locally
bundle install
rails db:migrate
rails server
```

**On your resume:** "Ruby on Rails — built a full CRUD application (MVC, ActiveRecord, RESTful routing)"

---

## TASK 2 — Deploy TD Fraud Analytics to AWS (1 day)
**Why:** Data Services Developer and Platform Developer both list cloud deployment.
**Goal:** Your existing Docker app running on AWS with a public URL.

### Step 1: Create a free AWS account
Go to: https://aws.amazon.com/free
- Use your personal email
- Free tier includes 750 hours/month of EC2 t2.micro for 12 months
- No cost if you follow these steps and stop the instance when done

### Step 2: Install AWS CLI
```bash
# Mac
brew install awscli

# Windows
# Download from: https://aws.amazon.com/cli/

# Configure with your AWS credentials
aws configure
# Enter: Access Key ID, Secret Access Key, region (us-east-1), output format (json)
# Get keys from: AWS Console → IAM → Your user → Security credentials
```

### Step 3: Launch an EC2 instance
```bash
# In AWS Console:
# 1. Go to EC2 → Launch Instance
# 2. Choose: Amazon Linux 2023 AMI (free tier eligible)
# 3. Instance type: t2.micro (free tier)
# 4. Create a key pair, download the .pem file
# 5. Security group: allow SSH (port 22) and HTTP (port 8000)
# 6. Launch

# Note your instance's Public IPv4 address
```

### Step 4: Connect and set up Docker
```bash
# Connect via SSH
chmod 400 your-key.pem
ssh -i your-key.pem ec2-user@YOUR_PUBLIC_IP

# Install Docker on the instance
sudo yum update -y
sudo yum install -y docker
sudo service docker start
sudo usermod -a -G docker ec2-user
# Log out and back in for group change to take effect
```

### Step 5: Deploy your app
```bash
# On your LOCAL machine — build and push to Docker Hub
docker build -t hailevu/td-fraud-analytics .
docker login
docker push hailevu/td-fraud-analytics

# On the EC2 INSTANCE
docker pull hailevu/td-fraud-analytics
docker run -d -p 8000:8000 hailevu/td-fraud-analytics python python/fraud_analytics.py
```

### Step 6: Verify it works
Open a browser: http://YOUR_PUBLIC_IP:8000

If you see output, it's deployed. Screenshot it for your portfolio.

### Step 7: Update your README
Add this section to your td-fraud-analytics README:
```markdown
## Deployment
Deployed on AWS EC2 (t2.micro, Amazon Linux 2023).
Docker containerised — pull and run with a single command.

Public endpoint: http://[YOUR_IP]:8000
```

**On your resume:** "Deployed on AWS EC2 · Docker containerised · public endpoint"

### IMPORTANT: Stop the instance when not demoing
AWS Console → EC2 → Select instance → Instance State → Stop
This prevents charges. Only start it when a recruiter asks for a demo.

---

## TASK 3 — IBM watsonx Demo (2–3 days)
**Why:** Highest-signal thing you can do for IBM — shows you used their actual product.
**Goal:** Working Python scripts using watsonx.ai API + Lovable demo site.

### Step 1: Get IBM Cloud free account
Go to: https://cloud.ibm.com/registration
- Free tier — no credit card required for Lite plan
- Creates your IBM Cloud account (same ecosystem you'd use at IBM)

### Step 2: Provision watsonx.ai
1. In IBM Cloud console → Catalog → Search "watsonx.ai"
2. Select "Watson Machine Learning" → Create (Lite plan — free)
3. Go to: https://dataplatform.cloud.ibm.com/wx/home
4. Create a new Project
5. Get your API key: IBM Cloud → Manage → Access (IAM) → API keys → Create

### Step 3: Get your credentials
```bash
# You'll need:
# 1. IBM Cloud API key (from step above)
# 2. Project ID (from your watsonx project settings)
# 3. Region URL (e.g. https://us-south.ml.cloud.ibm.com)

# Set as environment variables
export IBM_API_KEY=your_api_key_here
export IBM_PROJECT_ID=your_project_id_here
export IBM_URL=https://us-south.ml.cloud.ibm.com
```

### Step 4: Run the Python scripts in this repo
```bash
pip install ibm-watsonx-ai pandas numpy
python python/watsonx_prompt_eval.py    # Demo 1
python python/watsonx_aml_demo.py       # Demo 2
python python/watsonx_gtm_demo.py       # Demo 3
```

### Step 5: Deploy to IBM Cloud Code Engine (free tier)
```bash
# Install IBM Cloud CLI
curl -fsSL https://cacher.icr.io/cli-installer.sh | sh

# Login
ibmcloud login --apikey $IBM_API_KEY
ibmcloud target -r us-south -g Default

# Install Code Engine plugin
ibmcloud plugin install code-engine

# Create Code Engine project and deploy
ibmcloud ce project create --name watsonx-demo
ibmcloud ce project select --name watsonx-demo
ibmcloud ce app create --name watsonx-demo \
  --image docker.io/hailevu/watsonx-demo \
  --port 8000

# Get your URL
ibmcloud ce app get --name watsonx-demo
```

### Step 6: Salesforce Trailhead (parallel — do while waiting for AWS/watsonx)
Go to: https://trailhead.salesforce.com
- Search "Admin Beginner" trail
- Complete all 5 modules (~8 hours total)
- Earn the badge → screenshot it
- Add to LinkedIn certifications section
- Add to resume: "Salesforce Certified — Trailhead Admin Beginner (2026)"

---

## Timeline

| Day | Task |
|---|---|
| Day 1 | Rails tutorial + CRUD app |
| Day 2 | Rails — extend app, push to GitHub |
| Day 3 | AWS account + EC2 setup + deploy |
| Day 4 | IBM Cloud account + watsonx credentials + run scripts |
| Day 5 | watsonx scripts working, push to GitHub |
| Day 6 | Salesforce Trailhead (modules 1-3) |
| Day 7 | Salesforce Trailhead (modules 4-5) + badge earned |
| Day 8 | Deploy watsonx demo to IBM Cloud Code Engine |
| Done | Update resumes with completed credentials |

**While doing all this:** Submit applications NOW with the forward-looking resumes.
Get the referral submitted same day or before.
