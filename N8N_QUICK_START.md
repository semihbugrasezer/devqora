# 🚀 **n8n Quick Start Guide**

## 🎯 **Get Your Automation Running in 5 Minutes!**

---

## 📋 **Step 1: Access n8n Dashboard**

1. **Open your browser**
2. **Go to**: `https://n8n.hing.me`
3. **First time?** Create your admin account
4. **You'll see** the n8n workflow editor

---

## 📥 **Step 2: Import the Automation Workflow**

### **Option A: Import from File**
1. Click **"Import from file"** button
2. Select: `n8n_workflow_hing_playu.json`
3. Click **"Import"**

### **Option B: Copy-Paste Workflow**
1. Click **"Import from URL or text"**
2. Copy the entire content of `n8n_workflow_hing_playu.json`
3. Paste and click **"Import"**

---

## 🔧 **Step 3: Configure the Workflow**

### **Review the Nodes:**
- **Daily Trigger**: Runs at 9 AM every day
- **Fetch API Data**: Gets content ideas from public APIs
- **Generate Content**: Creates content for both domains
- **Enqueue Keywords**: Adds keywords to Pinterest queue
- **Create Articles**: Generates .astro pages via Content API
- **Build Sites**: Automatically rebuilds and deploys sites

### **Important Settings:**
- **Daily Trigger**: Set to 9:00 AM (or your preferred time)
- **Content Generation**: Configure for your domains
- **API Endpoints**: Already configured for your local services

---

## 🚀 **Step 4: Activate Automation**

1. **Click the "Toggle" button** (top right)
2. **Workflow status** changes to "Active"
3. **Automation starts** running daily at 9 AM
4. **Monitor executions** in real-time

---

## 📊 **Step 5: Test the Workflow**

### **Manual Test Run:**
1. Click **"Execute Workflow"** button
2. Watch the execution in real-time
3. Check the **Execution Log** for results
4. Verify content was generated

### **Expected Results:**
- ✅ Content API receives requests
- ✅ New .astro files created
- ✅ Keywords added to Redis queue
- ✅ Sites rebuild successfully

---

## 🔍 **Step 6: Monitor & Debug**

### **View Executions:**
- **Executions tab**: See all workflow runs
- **Real-time logs**: Watch as it runs
- **Error handling**: Check for any issues

### **Common Issues:**
- **Content API not responding**: Check if service is running
- **Build failures**: Check site configuration
- **Permission errors**: Verify file permissions

---

## 📈 **Step 7: Scale & Optimize**

### **Daily Monitoring:**
- Check execution logs
- Review generated content
- Monitor site performance
- Track keyword queue growth

### **Weekly Optimization:**
- Review content quality
- Adjust generation parameters
- Monitor AdSense performance
- Plan domain expansion

---

## 🎯 **What Happens Next**

### **Daily at 9 AM:**
1. **Workflow triggers automatically**
2. **Generates 5-10 articles per domain**
3. **Queues Pinterest keywords**
4. **Rebuilds and deploys sites**
5. **Ready for monetization**

### **Expected Output:**
- **Week 1**: 35-70 articles across both domains
- **Month 1**: 150-300 articles total
- **Month 3**: 500+ articles with traffic growth
- **Revenue**: $50-200/month (after AdSense setup)

---

## 🚨 **Troubleshooting**

### **Workflow Won't Import:**
- Check file format (must be valid JSON)
- Verify n8n version compatibility
- Try copy-paste method instead

### **Workflow Won't Activate:**
- Check all nodes are properly configured
- Verify API endpoints are accessible
- Check execution logs for errors

### **Content Not Generating:**
- Verify Content API is running
- Check API health: `http://localhost:7055/health`
- Review Content API logs

---

## 📞 **Need Help?**

### **System Commands:**
```bash
# Check system health
./scripts/health.sh

# Test automation
./scripts/test_automation.sh

# View service logs
docker compose logs [service-name]

# Restart services
docker compose restart
```

### **Documentation:**
- **`AUTOMATION_SETUP_GUIDE.md`**: Detailed setup guide
- **`FINAL_STATUS_REPORT.md`**: Complete system overview
- **`DEPLOYMENT_STATUS.md`**: Deployment details

---

## 🎉 **Success Checklist**

- [ ] n8n dashboard accessible
- [ ] Workflow imported successfully
- [ ] All nodes configured properly
- [ ] Workflow activated and running
- [ ] Test execution successful
- [ ] Content generation working
- [ ] Daily automation scheduled

---

## 🚀 **You're Ready to Launch!**

**Once this workflow is active, your system will:**
- Generate content automatically every day
- Build and deploy sites without intervention
- Queue keywords for traffic generation
- Scale to multiple domains easily
- Generate passive income through AdSense

**🎯 The next step is setting up custom domains and AdSense to start earning money!**

---

**⏰ Estimated setup time: 5-10 minutes**
**🔄 Automation runtime: ~5 minutes per day**
**📈 Expected monthly revenue: $50-200 (after AdSense setup)**
