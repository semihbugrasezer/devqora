# 🚀 **n8n Automation Setup Guide - Hing.me & Playu.co**

## **Overview**
This guide will help you set up the automated content generation system using n8n. The workflow will:
- **Generate 5-10 articles daily** for both domains
- **Automatically build and deploy** sites to Cloudflare Pages
- **Enqueue keywords** for Pinterest automation
- **Run every day at 9:00 AM** automatically

---

## **📋 Step 1: Access n8n Dashboard**

1. **Open your browser** and go to: `https://n8n.hing.me`
2. **Create admin account** on first visit:
   - Enter your email
   - Create a strong password
   - Complete the setup

---

## **📥 Step 2: Import the Workflow**

1. **Click "Import from file"** in the top right
2. **Select the file**: `n8n_workflow_hing_playu_enhanced.json`
3. **Click "Import"** to load the workflow

---

## **⚙️ Step 3: Configure the Workflow**

### **3.1 Review Workflow Structure**
The workflow contains these main components:
- **Daily Trigger** (Cron - 9:00 AM daily)
- **Content Generation** (Finance + Gaming APIs)
- **Article Creation** (Content API calls)
- **Keyword Enqueuing** (Bot API calls)
- **Site Building** (Build script execution)
- **Deployment** (Cloudflare Pages deployment)

### **3.2 Test the Workflow First**
1. **Click "Execute Workflow"** button
2. **Watch the execution** in real-time
3. **Check for any errors** in the execution log
4. **Verify all nodes complete** successfully

---

## **🔧 Step 4: Activate Automation**

1. **Click the "Toggle" button** to activate the workflow
2. **Confirm activation** when prompted
3. **The workflow will now run automatically** every day at 9:00 AM

---

## **📊 Step 5: Monitor & Verify**

### **5.1 Check Content Generation**
After the first run, verify:
- **New articles created** in both domains
- **Content API logs** show successful ingestion
- **Sites build successfully** without errors

### **5.2 Monitor Automation**
- **Check n8n dashboard** daily for execution status
- **Review execution logs** for any issues
- **Verify site updates** on Cloudflare Pages

---

## **🎯 Expected Results**

### **Daily Output:**
- **5-10 new articles** per domain
- **Automatic site building** and deployment
- **Keywords enqueued** for Pinterest automation
- **Sites updated** with fresh content

### **Content Quality:**
- **Finance articles** for Hing.me (investment, APIs, guides)
- **Gaming articles** for Playu.co (gaming strategies, tips)
- **SEO-optimized** titles and descriptions
- **Professional appearance** with enhanced UI

---

## **🔍 Troubleshooting**

### **Common Issues:**

1. **Content API Not Responding**
   ```bash
   # Check if service is running
   docker compose ps content-api
   
   # Check logs
   docker compose logs content-api
   ```

2. **Build Scripts Fail**
   ```bash
   # Test build manually
   cd /srv/auto-adsense/multidomain_site_kit
   ./scripts/build-all.sh
   ```

3. **Deployment Issues**
   ```bash
   # Test deployment manually
   ./scripts/deploy-all.sh
   ```

### **Debug Commands:**
```bash
# Check all services
docker compose ps

# View recent logs
docker compose logs -n 50

# Test APIs manually
curl http://localhost:5055/health
curl http://localhost:5001/health
```

---

## **📈 Scaling & Optimization**

### **Increase Content Volume:**
- **Modify the workflow** to generate more articles
- **Add more API sources** for diverse content
- **Adjust timing** for multiple daily runs

### **Content Quality Improvements:**
- **Customize content templates** in function nodes
- **Add more specific categories** for each domain
- **Implement content validation** and filtering

---

## **🚀 Next Steps After Setup**

1. **Monitor first week** of automation
2. **Review generated content** quality
3. **Set up AdSense** integration
4. **Configure Pinterest automation** with real API keys
5. **Add more domains** to the system

---

## **📞 Support & Monitoring**

### **Daily Checks:**
- **n8n execution status** ✅
- **New articles published** ✅
- **Sites deployed successfully** ✅
- **No errors in logs** ✅

### **Weekly Reviews:**
- **Content quality assessment**
- **Traffic and engagement metrics**
- **AdSense performance review**
- **System optimization opportunities**

---

## **🎉 Success Metrics**

### **Week 1:**
- [ ] Workflow runs daily without errors
- [ ] 35-70 articles generated across both domains
- [ ] Sites build and deploy automatically
- [ ] Content appears professional and engaging

### **Month 1:**
- [ ] 150-300 articles published
- [ ] Consistent daily automation
- [ ] Improved site traffic
- [ ] AdSense approval progress

---

**🎯 Your automation system is now ready to generate consistent, high-quality content that will drive traffic and revenue!**
