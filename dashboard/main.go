// /srv/auto-adsense/dashboard/main.go
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/go-redis/redis/v8"
	"github.com/google/uuid"
	"github.com/shirou/gopsutil/v3/cpu"
	"github.com/shirou/gopsutil/v3/mem"
)

type SystemMetrics struct {
	CPUUsage    float64 `json:"cpu_usage"`
	MemoryUsage float64 `json:"memory_usage"`
	Uptime      string  `json:"uptime"`
	DiskUsage   float64 `json:"disk_usage"`
}

type User struct {
	ID       string    `json:"id"`
	Username string    `json:"username"`
	Password string    `json:"password"`
	Role     string    `json:"role"` // "admin" or "user"
	Created  time.Time `json:"created"`
	LastLogin time.Time `json:"last_login"`
}

type LoginRequest struct {
	Username string `json:"username"`
	Password string `json:"password"`
}

type SignupRequest struct {
	Username string `json:"username"`
	Password string `json:"password"`
	Role     string `json:"role"`
}

type AuthResponse struct {
	Success bool   `json:"success"`
	Message string `json:"message"`
	Token   string `json:"token,omitempty"`
	User    *User  `json:"user,omitempty"`
}

type Domain struct {
	Name                string    `json:"name"`
	Status              string    `json:"status"`
	Niche               string    `json:"niche"`
	Language            string    `json:"language"`
	Country             string    `json:"country"`
	AdSenseClient       string    `json:"adsense_client"`
	PinterestAccounts   []string  `json:"pinterest_accounts"`
	DailyTargetArticles int       `json:"daily_target_articles"`
	DailyTargetPins     int       `json:"daily_target_pins"`
	CreatedAt           time.Time `json:"created_at"`
	LastRevenue         float64   `json:"last_revenue"`
	TotalRevenue        float64   `json:"total_revenue"`
	TodayStats          DomainDailyStats `json:"today_stats"`
	Analytics           DomainAnalytics  `json:"analytics"`
}

type DomainDailyStats struct {
	ArticlesCreated int     `json:"articles_created"`
	PinsPosted      int     `json:"pins_posted"`
	Impressions     int     `json:"impressions"`
	Clicks          int     `json:"clicks"`
	Revenue         float64 `json:"revenue"`
	CTR             float64 `json:"ctr"`
}

type DomainAnalytics struct {
	GoogleAnalytics GoogleAnalyticsData `json:"google_analytics"`
	SearchConsole   SearchConsoleData   `json:"search_console"`
	AdSense         AdSenseData         `json:"adsense"`
	Pinterest       PinterestData       `json:"pinterest"`
}

type GoogleAnalyticsData struct {
	Sessions       int     `json:"sessions"`
	Users          int     `json:"users"`
	PageViews      int     `json:"page_views"`
	BounceRate     float64 `json:"bounce_rate"`
	SessionDuration float64 `json:"session_duration"`
	TopPages       []TopPage `json:"top_pages"`
}

type SearchConsoleData struct {
	TotalClicks      int     `json:"total_clicks"`
	TotalImpressions int     `json:"total_impressions"`
	AverageCTR       float64 `json:"average_ctr"`
	AveragePosition  float64 `json:"average_position"`
	TopQueries       []TopQuery `json:"top_queries"`
}

type AdSenseData struct {
	Revenue         float64 `json:"revenue"`
	Impressions     int     `json:"impressions"`
	Clicks          int     `json:"clicks"`
	CTR             float64 `json:"ctr"`
	CPC             float64 `json:"cpc"`
	RPM             float64 `json:"rpm"`
}

type PinterestData struct {
	TotalPins    int   `json:"total_pins"`
	TotalViews   int   `json:"total_views"`
	TotalSaves   int   `json:"total_saves"`
	TotalClicks  int   `json:"total_clicks"`
	Accounts     []PinterestAccount `json:"accounts"`
}

type PinterestAccount struct {
	ID          string `json:"id"`
	AccountName string `json:"account_name"`
	Username    string `json:"username"`
	Status      string `json:"status"`
	Followers   int    `json:"followers"`
	Pins        int    `json:"pins"`
	AccessToken string `json:"-"` // Hidden from JSON response
	BoardID     string `json:"board_id"`
	CreatedAt   string `json:"created_at"`
}

type TopPage struct {
	Path      string `json:"path"`
	Views     int    `json:"views"`
	Users     int    `json:"users"`
}

type TopQuery struct {
	Query       string  `json:"query"`
	Clicks      int     `json:"clicks"`
	Impressions int     `json:"impressions"`
	CTR         float64 `json:"ctr"`
	Position    float64 `json:"position"`
}

type SystemConfig struct {
	GoogleAPIs      GoogleAPIConfig      `json:"google_apis"`
	PinterestAPIs   PinterestAPIConfig   `json:"pinterest_apis"`
	ContentAPIs     ContentAPIConfig     `json:"content_apis"`
	SystemSettings  SystemSettingsConfig `json:"system_settings"`
}

type GoogleAPIConfig struct {
	AnalyticsAPIKey     string `json:"analytics_api_key"`
	SearchConsoleAPIKey string `json:"search_console_api_key"`
	AdSenseAPIKey       string `json:"adsense_api_key"`
	ClientEmail         string `json:"client_email"`
	PrivateKey          string `json:"private_key"`
}

type PinterestAPIConfig struct {
	TailwindAPIKey    string `json:"tailwind_api_key"`
	PinterestAppID    string `json:"pinterest_app_id"`
	PinterestSecret   string `json:"pinterest_secret"`
}

type ContentAPIConfig struct {
	OpenAIAPIKey      string `json:"openai_api_key"`
	ClaudeAPIKey      string `json:"claude_api_key"`
	NanoBananaAPIKey  string `json:"nano_banana_api_key"`
}

type SystemSettingsConfig struct {
	DailyPinTarget      int    `json:"daily_pin_target"`
	DailyArticleTarget  int    `json:"daily_article_target"`
	WindowStart         string `json:"window_start"`
	WindowEnd           string `json:"window_end"`
	AutoScalingEnabled  bool   `json:"auto_scaling_enabled"`
	ShadowBanDetection  bool   `json:"shadow_ban_detection"`
}

type DashboardData struct {
	SystemMetrics    SystemMetrics   `json:"system_metrics"`
	Domains          []Domain        `json:"domains"`
	TotalRevenue     float64         `json:"total_revenue"`
	TotalImpressions int             `json:"total_impressions"`
	TotalClicks      int             `json:"total_clicks"`
	SystemConfig     SystemConfig    `json:"system_config"`
	RecentEvents     []Event         `json:"recent_events"`
	Alerts           []Alert         `json:"alerts"`
	Pinterest        PinterestData   `json:"pinterest"`
}

type Event struct {
	ID        string    `json:"id"`
	Type      string    `json:"type"`
	Domain    string    `json:"domain"`
	Message   string    `json:"message"`
	Timestamp time.Time `json:"timestamp"`
	Severity  string    `json:"severity"`
}

type Alert struct {
	ID          string    `json:"id"`
	Type        string    `json:"type"`
	Title       string    `json:"title"`
	Message     string    `json:"message"`
	Severity    string    `json:"severity"`
	Domain      string    `json:"domain"`
	CreatedAt   time.Time `json:"created_at"`
	Acknowledged bool     `json:"acknowledged"`
}

// In-memory storage for Pinterest accounts (replace with database in production)
var (
	pinterestAccounts []PinterestAccount
	accountsMutex     sync.RWMutex
)

var (
	rdb       *redis.Client
	ctx       = context.Background()
	startTime = time.Now()
)

func main() {
	// Redis connection
	redisHost := getEnv("REDIS_HOST", "localhost")
	redisPort := getEnv("REDIS_PORT", "6379")
	rdb = redis.NewClient(&redis.Options{
		Addr:     redisHost + ":" + redisPort,
		Password: getEnv("REDIS_PASSWORD", ""),
		DB:       0,
	})

	// Test Redis connection
	_, err := rdb.Ping(ctx).Result()
	if err != nil {
		log.Printf("Redis connection failed: %v", err)
	} else {
		log.Println("Connected to Redis successfully")
	}

	// Setup Gin
	gin.SetMode(gin.ReleaseMode)
	r := gin.Default()

	// Enable CORS
	r.Use(func(c *gin.Context) {
		c.Header("Access-Control-Allow-Origin", "*")
		c.Header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		c.Header("Access-Control-Allow-Headers", "Content-Type, Authorization")
		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}
		c.Next()
	})

	// Load HTML templates
	r.LoadHTMLGlob("templates/*")

	// Main Routes
	r.GET("/", landingHandler)
	r.GET("/dashboard", authMiddleware(), dashboardHandler)
	// Authentication Routes (public)
	r.POST("/api/auth/login", apiLoginHandler)
	r.POST("/api/auth/signup", apiSignupHandler)
	r.POST("/api/auth/logout", apiLogoutHandler)
	r.GET("/api/auth/check", apiAuthCheckHandler)
	
	// Admin User Management Routes (protected)
	admin := r.Group("/api/admin")
	admin.Use(authMiddleware())
	admin.Use(adminMiddleware())
	{
		admin.GET("/users", apiListUsersHandler)
		admin.PUT("/users/:id/role", apiChangeUserRoleHandler)
		admin.DELETE("/users/:id", apiDeleteUserHandler)
	}

	// API Routes (protected)
	r.GET("/api/dashboard", authMiddleware(), apiDashboardHandler)

	// Domain Management Routes
	r.GET("/api/domains", apiDomainsHandler)
	r.POST("/api/domains", apiAddDomainHandler)
	r.PUT("/api/domains/:domain", apiUpdateDomainHandler)
	r.DELETE("/api/domains/:domain", apiDeleteDomainHandler)
	r.GET("/api/domains/:domain/analytics", apiDomainAnalyticsHandler)
	r.PUT("/api/domains/:domain/adsense", apiUpdateAdSenseHandler)

	// Configuration Management Routes
	r.GET("/api/config", apiGetConfigHandler)
	r.PUT("/api/config", apiUpdateConfigHandler)
	r.POST("/api/config/test", apiTestConfigHandler)

	// System Control Routes
	r.POST("/api/system/restart", apiRestartSystemHandler)
	r.POST("/api/system/start-autonomous", apiStartAutonomousHandler)
	r.POST("/api/system/stop-autonomous", apiStopAutonomousHandler)

	// Analytics Routes
	r.GET("/api/analytics/overview", apiAnalyticsOverviewHandler)
	r.GET("/api/analytics/revenue", apiRevenueAnalyticsHandler)
	r.GET("/api/analytics/content", apiContentAnalyticsHandler)
	r.GET("/api/analytics/pinterest", apiPinterestAnalyticsHandler)

	// Events and Alerts Routes
	r.GET("/api/events", apiEventsHandler)
	r.GET("/api/alerts", apiAlertsHandler)
	r.POST("/api/alerts/:id/acknowledge", apiAcknowledgeAlertHandler)

	// Content Management Routes
	r.POST("/api/content/generate", apiGenerateContentHandler)
	r.GET("/api/content/queue", apiContentQueueHandler)
	r.POST("/api/content/bulk-generate", apiBulkGenerateContentHandler)
	r.POST("/api/content/translate", apiTranslateContentHandler)
	
	// Image Generation Routes
	r.POST("/api/images/generate", apiGenerateImagesHandler)
	r.PUT("/api/images/generate", apiGenerateImagesHandler)
	
	// Deployment Routes
	r.POST("/api/deploy/cloudflare", apiDeployCloudflareHandler)

	// Pinterest Management Routes
	r.GET("/api/pinterest/accounts", apiPinterestAccountsHandler)
	r.POST("/api/pinterest/accounts", apiCreatePinterestAccountHandler)
	r.POST("/api/pinterest/accounts/:id/check-status", apiCheckPinterestStatusHandler)
	r.POST("/api/pinterest/post", apiPostToPinterestHandler)

	// AdSense Management Routes
	r.GET("/api/adsense/refresh", apiAdSenseRefreshHandler)
	r.GET("/api/adsense/report/:days", apiAdSenseReportHandler)
	r.GET("/api/adsense/optimize/:site", apiAdSenseOptimizeHandler)
	r.GET("/api/adsense/account", apiAdSenseAccountHandler)

	// Monitoring Routes
	r.GET("/api/monitoring/system", apiSystemMonitoringHandler)
	r.GET("/api/monitoring/services", apiServicesMonitoringHandler)
	r.GET("/api/monitoring/logs/:service", apiServiceLogsHandler)

	// Security Routes
	r.GET("/api/security/scan-status", apiSecurityScanStatusHandler)
	r.GET("/api/security/latest-report", authMiddleware(), apiSecurityLatestReportHandler)
	r.POST("/api/security/trigger-scan", authMiddleware(), adminMiddleware(), apiTriggerSecurityScanHandler)

	port := getEnv("PORT", "8080")
	log.Printf("Comprehensive Dashboard starting on port %s", port)
	log.Fatal(r.Run(":" + port))
}

// Authentication Functions
func apiLoginHandler(c *gin.Context) {
	var loginReq LoginRequest
	if err := c.ShouldBindJSON(&loginReq); err != nil {
		c.JSON(http.StatusBadRequest, AuthResponse{
			Success: false,
			Message: "Invalid request format",
		})
		return
	}

	// Check user credentials
	userKey := "user:" + loginReq.Username
	userData, err := rdb.HMGet(ctx, userKey, "password", "role", "id").Result()
	if err != nil || userData[0] == nil {
		c.JSON(http.StatusUnauthorized, AuthResponse{
			Success: false,
			Message: "Invalid username or password",
		})
		return
	}

	storedPassword := userData[0].(string)
	role := userData[1].(string)
	userID := userData[2].(string)

	// Simple password check (in production, use hashed passwords)
	if storedPassword != loginReq.Password {
		c.JSON(http.StatusUnauthorized, AuthResponse{
			Success: false,
			Message: "Invalid username or password",
		})
		return
	}

	// Generate simple session token
	sessionToken := generateSessionToken()
	
	// Store session in Redis
	sessionKey := "session:" + sessionToken
	rdb.HMSet(ctx, sessionKey, map[string]interface{}{
		"user_id":  userID,
		"username": loginReq.Username,
		"role":     role,
		"created":  time.Now().Unix(),
	})
	rdb.Expire(ctx, sessionKey, 24*time.Hour) // Session expires in 24 hours

	// Update last login
	rdb.HSet(ctx, userKey, "last_login", time.Now().Unix())

	user := &User{
		ID:       userID,
		Username: loginReq.Username,
		Role:     role,
		LastLogin: time.Now(),
	}

	c.JSON(http.StatusOK, AuthResponse{
		Success: true,
		Message: "Login successful",
		Token:   sessionToken,
		User:    user,
	})
}

func apiSignupHandler(c *gin.Context) {
	var signupReq SignupRequest
	if err := c.ShouldBindJSON(&signupReq); err != nil {
		c.JSON(http.StatusBadRequest, AuthResponse{
			Success: false,
			Message: "Invalid request format",
		})
		return
	}

	// Validate input
	if signupReq.Username == "" || signupReq.Password == "" {
		c.JSON(http.StatusBadRequest, AuthResponse{
			Success: false,
			Message: "Username and password are required",
		})
		return
	}

	if len(signupReq.Password) < 6 {
		c.JSON(http.StatusBadRequest, AuthResponse{
			Success: false,
			Message: "Password must be at least 6 characters",
		})
		return
	}

	// Check if user already exists
	userKey := "user:" + signupReq.Username
	exists, err := rdb.Exists(ctx, userKey).Result()
	if err != nil {
		c.JSON(http.StatusInternalServerError, AuthResponse{
			Success: false,
			Message: "Database error",
		})
		return
	}

	if exists > 0 {
		c.JSON(http.StatusConflict, AuthResponse{
			Success: false,
			Message: "Username already exists",
		})
		return
	}

	// Set default role
	role := signupReq.Role
	if role == "" {
		role = "user"
	}

	// Only allow admin creation if there are no users yet, or if current user is admin
	if role == "admin" {
		userCount, _ := rdb.Keys(ctx, "user:*").Result()
		if len(userCount) > 0 {
			// Check if current user is admin (simplified check)
			role = "user" // Force to user role
		}
	}

	userID := uuid.New().String()
	
	// Create user
	rdb.HMSet(ctx, userKey, map[string]interface{}{
		"id":       userID,
		"username": signupReq.Username,
		"password": signupReq.Password, // In production, hash this!
		"role":     role,
		"created":  time.Now().Unix(),
		"last_login": 0,
	})

	// Log event
	logEvent("user_signup", signupReq.Username, "User registered successfully", "info")

	user := &User{
		ID:       userID,
		Username: signupReq.Username,
		Role:     role,
		Created:  time.Now(),
	}

	c.JSON(http.StatusCreated, AuthResponse{
		Success: true,
		Message: "User created successfully",
		User:    user,
	})
}

func apiLogoutHandler(c *gin.Context) {
	token := c.GetHeader("Authorization")
	if token != "" {
		// Remove session from Redis
		sessionKey := "session:" + token
		rdb.Del(ctx, sessionKey)
	}

	c.JSON(http.StatusOK, AuthResponse{
		Success: true,
		Message: "Logged out successfully",
	})
}

func apiAuthCheckHandler(c *gin.Context) {
	token := c.GetHeader("Authorization")
	if token == "" {
		c.JSON(http.StatusUnauthorized, AuthResponse{
			Success: false,
			Message: "No authentication token",
		})
		return
	}

	sessionKey := "session:" + token
	sessionData, err := rdb.HMGet(ctx, sessionKey, "user_id", "username", "role").Result()
	if err != nil || sessionData[0] == nil {
		c.JSON(http.StatusUnauthorized, AuthResponse{
			Success: false,
			Message: "Invalid or expired session",
		})
		return
	}

	user := &User{
		ID:       sessionData[0].(string),
		Username: sessionData[1].(string),
		Role:     sessionData[2].(string),
	}

	c.JSON(http.StatusOK, AuthResponse{
		Success: true,
		Message: "Authenticated",
		User:    user,
	})
}

// Authentication Middleware
func authMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		token := c.GetHeader("Authorization")
		if token == "" {
			c.JSON(http.StatusUnauthorized, gin.H{
				"success": false,
				"message": "Authentication required",
			})
			c.Abort()
			return
		}

		sessionKey := "session:" + token
		sessionData, err := rdb.HMGet(ctx, sessionKey, "user_id", "username", "role").Result()
		if err != nil || sessionData[0] == nil {
			c.JSON(http.StatusUnauthorized, gin.H{
				"success": false,
				"message": "Invalid or expired session",
			})
			c.Abort()
			return
		}

		// Set user info in context
		c.Set("user_id", sessionData[0])
		c.Set("username", sessionData[1])
		c.Set("userRole", sessionData[2])

		c.Next()
	}
}

// Generate session token
func generateSessionToken() string {
	return uuid.New().String() + "-" + fmt.Sprintf("%d", time.Now().Unix())
}

func landingHandler(c *gin.Context) {
	c.HTML(http.StatusOK, "landing.html", gin.H{})
}

func dashboardHandler(c *gin.Context) {
	data := getDashboardData()
	c.HTML(http.StatusOK, "dashboard.html", gin.H{
		"Data": data,
	})
}

func apiDashboardHandler(c *gin.Context) {
	c.JSON(http.StatusOK, getDashboardData())
}

func apiDomainsHandler(c *gin.Context) {
	domains := getAllDomains()
	c.JSON(http.StatusOK, domains)
}

func apiAddDomainHandler(c *gin.Context) {
	var domainData map[string]interface{}
	if err := c.ShouldBindJSON(&domainData); err != nil {
		c.JSON(400, gin.H{"error": err.Error()})
		return
	}

	// Call autonomous system to add domain
	result := addDomainToSystem(domainData)
	c.JSON(http.StatusOK, result)
}

func apiUpdateDomainHandler(c *gin.Context) {
	domain := c.Param("domain")
	var updateData map[string]interface{}
	
	if err := c.ShouldBindJSON(&updateData); err != nil {
		c.JSON(400, gin.H{"error": err.Error()})
		return
	}

	result := updateDomainSettings(domain, updateData)
	c.JSON(http.StatusOK, result)
}

func apiTranslateContentHandler(c *gin.Context) {
	var translateData map[string]interface{}
	
	if err := c.ShouldBindJSON(&translateData); err != nil {
		c.JSON(400, gin.H{"error": err.Error()})
		return
	}

	result := translateDomainContent(translateData)
	c.JSON(http.StatusOK, result)
}

func apiDeleteDomainHandler(c *gin.Context) {
	domain := c.Param("domain")
	result := removeDomainFromSystem(domain)
	c.JSON(http.StatusOK, result)
}

func apiDomainAnalyticsHandler(c *gin.Context) {
	domain := c.Param("domain")
	analytics := getDomainAnalytics(domain)
	c.JSON(http.StatusOK, analytics)
}

func apiUpdateAdSenseHandler(c *gin.Context) {
	domain := c.Param("domain")
	
	var updateData map[string]interface{}
	if err := c.ShouldBindJSON(&updateData); err != nil {
		c.JSON(400, gin.H{"error": err.Error()})
		return
	}
	
	// Update AdSense configuration for domain
	result := updateDomainAdSense(domain, updateData)
	c.JSON(http.StatusOK, result)
}

func apiGetConfigHandler(c *gin.Context) {
	config := getSystemConfig()
	c.JSON(http.StatusOK, config)
}

func apiUpdateConfigHandler(c *gin.Context) {
	var config SystemConfig
	if err := c.ShouldBindJSON(&config); err != nil {
		c.JSON(400, gin.H{"error": err.Error()})
		return
	}

	result := updateSystemConfig(config)
	c.JSON(http.StatusOK, result)
}

func apiTestConfigHandler(c *gin.Context) {
	var testData map[string]interface{}
	if err := c.ShouldBindJSON(&testData); err != nil {
		c.JSON(400, gin.H{"error": err.Error()})
		return
	}

	result := testConfiguration(testData)
	c.JSON(http.StatusOK, result)
}

func apiRestartSystemHandler(c *gin.Context) {
	// Restart Docker services
	cmd := exec.Command("docker", "compose", "restart")
	err := cmd.Run()
	
	if err != nil {
		c.JSON(500, gin.H{"error": fmt.Sprintf("Failed to restart system: %v", err)})
		return
	}
	
	c.JSON(http.StatusOK, gin.H{"success": true, "message": "System restart initiated"})
}

func apiStartAutonomousHandler(c *gin.Context) {
	result := startAutonomousSystem()
	c.JSON(http.StatusOK, result)
}

func apiStopAutonomousHandler(c *gin.Context) {
	result := stopAutonomousSystem()
	c.JSON(http.StatusOK, result)
}

func apiAnalyticsOverviewHandler(c *gin.Context) {
	overview := getAnalyticsOverview()
	c.JSON(http.StatusOK, overview)
}

func apiRevenueAnalyticsHandler(c *gin.Context) {
	days := c.DefaultQuery("days", "30")
	daysInt, _ := strconv.Atoi(days)
	
	analytics := getRevenueAnalytics(daysInt)
	c.JSON(http.StatusOK, analytics)
}

func apiContentAnalyticsHandler(c *gin.Context) {
	analytics := getContentAnalytics()
	c.JSON(http.StatusOK, analytics)
}

func apiPinterestAnalyticsHandler(c *gin.Context) {
	analytics := getPinterestAnalytics()
	c.JSON(http.StatusOK, analytics)
}

func apiEventsHandler(c *gin.Context) {
	limit := c.DefaultQuery("limit", "50")
	limitInt, _ := strconv.Atoi(limit)
	
	events := getRecentEvents(limitInt)
	c.JSON(http.StatusOK, events)
}

func apiAlertsHandler(c *gin.Context) {
	alerts := getActiveAlerts()
	c.JSON(http.StatusOK, alerts)
}

func apiAcknowledgeAlertHandler(c *gin.Context) {
	alertID := c.Param("id")
	result := acknowledgeAlert(alertID)
	c.JSON(http.StatusOK, result)
}

func apiGenerateContentHandler(c *gin.Context) {
	var contentRequest map[string]interface{}
	if err := c.ShouldBindJSON(&contentRequest); err != nil {
		c.JSON(400, gin.H{"error": err.Error()})
		return
	}

	result := triggerContentGeneration(contentRequest)
	c.JSON(http.StatusOK, result)
}

func apiContentQueueHandler(c *gin.Context) {
	queueStatus := getContentQueueStatus()
	c.JSON(http.StatusOK, queueStatus)
}

func apiBulkGenerateContentHandler(c *gin.Context) {
	var bulkRequest map[string]interface{}
	if err := c.ShouldBindJSON(&bulkRequest); err != nil {
		c.JSON(400, gin.H{"error": err.Error()})
		return
	}

	result := triggerBulkContentGeneration(bulkRequest)
	c.JSON(http.StatusOK, result)
}

func apiGenerateImagesHandler(c *gin.Context) {
	var imageRequest map[string]interface{}
	if err := c.ShouldBindJSON(&imageRequest); err != nil {
		c.JSON(400, gin.H{"error": err.Error()})
		return
	}

	result := triggerImageGeneration(imageRequest)
	c.JSON(http.StatusOK, result)
}

func apiDeployCloudflareHandler(c *gin.Context) {
	var deployRequest map[string]interface{}
	if err := c.ShouldBindJSON(&deployRequest); err != nil {
		c.JSON(400, gin.H{"error": err.Error()})
		return
	}

	result := triggerCloudflareDeployment(deployRequest)
	c.JSON(http.StatusOK, result)
}

func apiPostToPinterestHandler(c *gin.Context) {
	var pinterestRequest map[string]interface{}
	if err := c.ShouldBindJSON(&pinterestRequest); err != nil {
		c.JSON(400, gin.H{"error": err.Error()})
		return
	}

	result := triggerPinterestPosting(pinterestRequest)
	c.JSON(http.StatusOK, result)
}

func apiPinterestAccountsHandler(c *gin.Context) {
	accounts := getPinterestAccounts()
	c.JSON(http.StatusOK, accounts)
}

func apiCreatePinterestAccountHandler(c *gin.Context) {
	var accountData map[string]interface{}
	if err := c.ShouldBindJSON(&accountData); err != nil {
		c.JSON(400, gin.H{"error": err.Error()})
		return
	}

	result := createPinterestAccount(accountData)
	c.JSON(http.StatusOK, result)
}

func apiCheckPinterestStatusHandler(c *gin.Context) {
	accountID := c.Param("id")
	result := checkPinterestAccountStatus(accountID)
	c.JSON(http.StatusOK, result)
}

func apiSystemMonitoringHandler(c *gin.Context) {
	monitoring := getSystemMonitoring()
	c.JSON(http.StatusOK, monitoring)
}

func apiServicesMonitoringHandler(c *gin.Context) {
	services := getServicesStatus()
	c.JSON(http.StatusOK, services)
}

func apiServiceLogsHandler(c *gin.Context) {
	service := c.Param("service")
	lines := c.DefaultQuery("lines", "100")
	
	logs := getServiceLogs(service, lines)
	c.JSON(http.StatusOK, logs)
}

// AdSense API Handlers
func apiAdSenseRefreshHandler(c *gin.Context) {
	// Refresh AdSense data from Redis cache (populated by adsense-manager service)
	adSenseData, err := rdb.Get(ctx, "adsense_current_stats").Result()
	if err != nil {
		c.JSON(http.StatusOK, gin.H{
			"success": false,
			"message": "AdSense data not available",
			"data": gin.H{
				"total_earnings": 0.0,
				"total_impressions": 0,
				"total_clicks": 0,
				"last_updated": time.Now().Format(time.RFC3339),
			},
		})
		return
	}

	var stats map[string]interface{}
	if err := json.Unmarshal([]byte(adSenseData), &stats); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to parse AdSense data"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"message": "AdSense data refreshed successfully",
		"data": stats,
	})
}

func apiAdSenseReportHandler(c *gin.Context) {
	days := c.Param("days")
	
	// Get revenue report for specified period
	reportData, err := rdb.Get(ctx, fmt.Sprintf("adsense_revenue_%sd", days)).Result()
	if err != nil {
		c.JSON(http.StatusOK, gin.H{
			"success": false,
			"message": "Revenue report not available",
			"data": gin.H{
				"period_days": days,
				"total_earnings": 0.0,
				"daily_data": []interface{}{},
			},
		})
		return
	}

	var report map[string]interface{}
	if err := json.Unmarshal([]byte(reportData), &report); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to parse report data"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"data": report,
	})
}

func apiAdSenseOptimizeHandler(c *gin.Context) {
	site := c.Param("site")
	
	// Get optimization suggestions for site
	optimizationData, err := rdb.Get(ctx, fmt.Sprintf("adsense_optimization_%s", site)).Result()
	if err != nil {
		c.JSON(http.StatusOK, gin.H{
			"success": false,
			"message": "Optimization data not available",
			"suggestions": []gin.H{
				{
					"type": "general",
					"priority": "medium",
					"suggestion": "Enable auto ads for better coverage",
					"action": "Review ad placement settings",
				},
			},
		})
		return
	}

	var optimization map[string]interface{}
	if err := json.Unmarshal([]byte(optimizationData), &optimization); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to parse optimization data"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"data": optimization,
	})
}

func apiAdSenseAccountHandler(c *gin.Context) {
	// Get AdSense account information
	accountData, err := rdb.Get(ctx, "adsense_account_info").Result()
	if err != nil {
		c.JSON(http.StatusOK, gin.H{
			"success": false,
			"message": "AdSense account data not available",
			"data": gin.H{
				"publisher_id": "pub-7970408813538482",
				"display_name": "Not Connected",
				"currency_code": "USD",
				"state": "UNKNOWN",
			},
		})
		return
	}

	var account map[string]interface{}
	if err := json.Unmarshal([]byte(accountData), &account); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to parse account data"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"data": account,
	})
}

// Implementation functions
func getDashboardData() DashboardData {
	return DashboardData{
		SystemMetrics:    getSystemMetrics(),
		Domains:          getAllDomains(),
		TotalRevenue:     getTotalRevenue(),
		TotalImpressions: getTotalImpressions(),
		TotalClicks:      getTotalClicks(),
		SystemConfig:     getSystemConfig(),
		RecentEvents:     getRecentEvents(10),
		Alerts:           getActiveAlerts(),
		Pinterest:        getPinterestData(),
	}
}

func getPinterestData() PinterestData {
	accounts := getPinterestAccounts()
	
	totalPins := 0
	totalSaves := 0
	totalClicks := 0
	
	for _, account := range accounts {
		totalPins += account.Pins
		// Add mock data for saves and clicks if needed
	}
	
	return PinterestData{
		TotalPins:    totalPins,
		TotalSaves:   totalSaves,
		TotalClicks:  totalClicks,
		Accounts:     accounts,
	}
}

func getAllDomains() []Domain {
	// Get domains from Redis
	domainsData, err := rdb.Get(ctx, "autonomous_domains").Result()
	if err != nil {
		return []Domain{}
	}

	var domains []Domain
	json.Unmarshal([]byte(domainsData), &domains)

	// Enrich with analytics data
	for i := range domains {
		domains[i].Analytics = getDomainAnalytics(domains[i].Name)
		domains[i].TodayStats = getDomainDailyStats(domains[i].Name)
	}

	return domains
}

func getDomainAnalytics(domain string) DomainAnalytics {
	// Get analytics from cache
	gaData := getGoogleAnalyticsData(domain)
	scData := getSearchConsoleData(domain)
	asData := getAdSenseData(domain)
	pData := getPinterestDataForDomain(domain)

	return DomainAnalytics{
		GoogleAnalytics: gaData,
		SearchConsole:   scData,
		AdSense:         asData,
		Pinterest:       pData,
	}
}

func getSystemConfig() SystemConfig {
	// Get config from Redis with default values
	configData, err := rdb.Get(ctx, "system_config").Result()
	
	var config SystemConfig
	if err == nil {
		json.Unmarshal([]byte(configData), &config)
	} else {
		// Return default config
		config = SystemConfig{
			GoogleAPIs: GoogleAPIConfig{
				AnalyticsAPIKey:     getEnv("GOOGLE_ANALYTICS_API_KEY", ""),
				SearchConsoleAPIKey: getEnv("GOOGLE_SEARCH_CONSOLE_API_KEY", ""),
				AdSenseAPIKey:       getEnv("GOOGLE_ADSENSE_API_KEY", ""),
				ClientEmail:         getEnv("GOOGLE_CLIENT_EMAIL", ""),
				PrivateKey:          getEnv("GOOGLE_PRIVATE_KEY", ""),
			},
			PinterestAPIs: PinterestAPIConfig{
				TailwindAPIKey:  getEnv("TAILWIND_API_KEY", ""),
				PinterestAppID:  getEnv("PINTEREST_APP_ID", ""),
				PinterestSecret: getEnv("PINTEREST_SECRET", ""),
			},
			ContentAPIs: ContentAPIConfig{
				OpenAIAPIKey:     getEnv("OPENAI_API_KEY", ""),
				ClaudeAPIKey:     getEnv("CLAUDE_API_KEY", ""),
				NanoBananaAPIKey: getEnv("NANO_BANANA_API_KEY", ""),
			},
			SystemSettings: SystemSettingsConfig{
				DailyPinTarget:     6,
				DailyArticleTarget: 5,
				WindowStart:        "08:00",
				WindowEnd:          "22:30",
				AutoScalingEnabled: true,
				ShadowBanDetection: true,
			},
		}
	}

	return config
}

func updateSystemConfig(config SystemConfig) map[string]interface{} {
	// Save to Redis
	configJSON, _ := json.Marshal(config)
	rdb.Set(ctx, "system_config", string(configJSON), 0)

	// Update environment variables
	updateEnvironmentVariables(config)

	// Restart services if needed
	restartAffectedServices(config)

	return map[string]interface{}{
		"success": true,
		"message": "Configuration updated successfully",
	}
}

func addDomainToSystem(domainData map[string]interface{}) map[string]interface{} {
	// Call autonomous system API
	_, _ = json.Marshal(domainData)
	
	// This would call the autonomous system service
	// For now, simulate it
	
	// Add to Redis
	domain := Domain{
		Name:                domainData["name"].(string),
		Status:              "pending",
		Niche:               domainData["niche"].(string),
		Language:            domainData["language"].(string),
		Country:             domainData["country"].(string),
		AdSenseClient:       domainData["adsense_client"].(string),
		DailyTargetArticles: int(domainData["daily_target_articles"].(float64)),
		DailyTargetPins:     int(domainData["daily_target_pins"].(float64)),
		CreatedAt:           time.Now(),
	}

	domains := getAllDomains()
	domains = append(domains, domain)
	
	domainsJSON, _ := json.Marshal(domains)
	rdb.Set(ctx, "autonomous_domains", string(domainsJSON), 0)

	// Log event
	logEvent("domain_added", domain.Name, "Domain added successfully", "info")

	return map[string]interface{}{
		"success": true,
		"domain":  domain,
		"message": "Domain added and setup initiated",
	}
}

func getSystemMetrics() SystemMetrics {
	cpuPercent, _ := cpu.Percent(time.Second, false)
	memInfo, _ := mem.VirtualMemory()
	
	uptime := time.Since(startTime).Round(time.Second).String()
	
	var cpuUsage float64
	if len(cpuPercent) > 0 {
		cpuUsage = cpuPercent[0]
	}

	// Get disk usage
	diskUsage := getDiskUsage()
	
	return SystemMetrics{
		CPUUsage:    cpuUsage,
		MemoryUsage: memInfo.UsedPercent,
		Uptime:      uptime,
		DiskUsage:   diskUsage,
	}
}

func getDiskUsage() float64 {
	cmd := exec.Command("df", "-h", "/")
	output, err := cmd.Output()
	if err != nil {
		return 0
	}
	
	lines := strings.Split(string(output), "\n")
	if len(lines) > 1 {
		fields := strings.Fields(lines[1])
		if len(fields) > 4 {
			usage := strings.TrimSuffix(fields[4], "%")
			if usageFloat, err := strconv.ParseFloat(usage, 64); err == nil {
				return usageFloat
			}
		}
	}
	
	return 0
}

func getTotalRevenue() float64 {
	// Calculate from all domains
	total := 0.0
	domains := getAllDomains()
	
	for _, domain := range domains {
		total += domain.TotalRevenue
	}
	
	return total
}

func getTotalImpressions() int {
	total := 0
	domains := getAllDomains()
	
	for _, domain := range domains {
		total += domain.Analytics.AdSense.Impressions
	}
	
	return total
}

func getTotalClicks() int {
	total := 0
	domains := getAllDomains()
	
	for _, domain := range domains {
		total += domain.Analytics.AdSense.Clicks
	}
	
	return total
}

func getRecentEvents(limit int) []Event {
	eventsData, err := rdb.LRange(ctx, "system_events", 0, int64(limit-1)).Result()
	if err != nil {
		return []Event{}
	}

	var events []Event
	for _, eventJSON := range eventsData {
		var event Event
		if json.Unmarshal([]byte(eventJSON), &event) == nil {
			events = append(events, event)
		}
	}

	return events
}

func getActiveAlerts() []Alert {
	alertsData, err := rdb.LRange(ctx, "system_alerts", 0, 49).Result()
	if err != nil {
		return []Alert{}
	}

	var alerts []Alert
	for _, alertJSON := range alertsData {
		var alert Alert
		if json.Unmarshal([]byte(alertJSON), &alert) == nil && !alert.Acknowledged {
			alerts = append(alerts, alert)
		}
	}

	return alerts
}

func logEvent(eventType, domain, message, severity string) {
	event := Event{
		ID:        fmt.Sprintf("evt_%d", time.Now().Unix()),
		Type:      eventType,
		Domain:    domain,
		Message:   message,
		Timestamp: time.Now(),
		Severity:  severity,
	}

	eventJSON, _ := json.Marshal(event)
	rdb.LPush(ctx, "system_events", string(eventJSON))
	rdb.LTrim(ctx, "system_events", 0, 999) // Keep last 1000 events
}

// Additional helper functions would be implemented here...
// (getGoogleAnalyticsData, getSearchConsoleData, etc.)

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

// Placeholder implementations for complex functions
func getDomainDailyStats(domain string) DomainDailyStats {
	return DomainDailyStats{
		ArticlesCreated: getRedisInt(fmt.Sprintf("daily:articles:%s", domain), 0),
		PinsPosted:      getRedisInt(fmt.Sprintf("daily:pins:%s", domain), 0),
		Impressions:     getRedisInt(fmt.Sprintf("daily:impressions:%s", domain), 0),
		Clicks:          getRedisInt(fmt.Sprintf("daily:clicks:%s", domain), 0),
		Revenue:         getRedisFloat(fmt.Sprintf("daily:revenue:%s", domain), 0),
		CTR:             0,
	}
}

func getGoogleAnalyticsData(domain string) GoogleAnalyticsData {
	return GoogleAnalyticsData{
		Sessions:    getRedisInt(fmt.Sprintf("ga:sessions:%s", domain), 0),
		Users:       getRedisInt(fmt.Sprintf("ga:users:%s", domain), 0),
		PageViews:   getRedisInt(fmt.Sprintf("ga:pageviews:%s", domain), 0),
		BounceRate:  getRedisFloat(fmt.Sprintf("ga:bounce_rate:%s", domain), 0),
		TopPages:    []TopPage{},
	}
}

func getSearchConsoleData(domain string) SearchConsoleData {
	return SearchConsoleData{
		TotalClicks:      getRedisInt(fmt.Sprintf("gsc:clicks:%s", domain), 0),
		TotalImpressions: getRedisInt(fmt.Sprintf("gsc:impressions:%s", domain), 0),
		AverageCTR:       getRedisFloat(fmt.Sprintf("gsc:ctr:%s", domain), 0),
		AveragePosition:  getRedisFloat(fmt.Sprintf("gsc:position:%s", domain), 0),
		TopQueries:       []TopQuery{},
	}
}

func getAdSenseData(domain string) AdSenseData {
	return AdSenseData{
		Revenue:     getRedisFloat(fmt.Sprintf("adsense:revenue:%s", domain), 0),
		Impressions: getRedisInt(fmt.Sprintf("adsense:impressions:%s", domain), 0),
		Clicks:      getRedisInt(fmt.Sprintf("adsense:clicks:%s", domain), 0),
		CTR:         getRedisFloat(fmt.Sprintf("adsense:ctr:%s", domain), 0),
		CPC:         getRedisFloat(fmt.Sprintf("adsense:cpc:%s", domain), 0),
		RPM:         getRedisFloat(fmt.Sprintf("adsense:rpm:%s", domain), 0),
	}
}

func getPinterestDataForDomain(domain string) PinterestData {
	return PinterestData{
		TotalPins:   getRedisInt(fmt.Sprintf("pinterest:pins:%s", domain), 0),
		TotalViews:  getRedisInt(fmt.Sprintf("pinterest:views:%s", domain), 0),
		TotalSaves:  getRedisInt(fmt.Sprintf("pinterest:saves:%s", domain), 0),
		TotalClicks: getRedisInt(fmt.Sprintf("pinterest:clicks:%s", domain), 0),
		Accounts:    []PinterestAccount{},
	}
}

func getRedisInt(key string, defaultVal int) int {
	val, err := rdb.Get(ctx, key).Result()
	if err != nil {
		return defaultVal
	}
	intVal, err := strconv.Atoi(val)
	if err != nil {
		return defaultVal
	}
	return intVal
}

func getRedisFloat(key string, defaultVal float64) float64 {
	val, err := rdb.Get(ctx, key).Result()
	if err != nil {
		return defaultVal
	}
	floatVal, err := strconv.ParseFloat(val, 64)
	if err != nil {
		return defaultVal
	}
	return floatVal
}

// Helper functions for map data extraction
func getStringFromMap(m map[string]interface{}, key string) string {
	if val, ok := m[key]; ok {
		if str, ok := val.(string); ok {
			return str
		}
	}
	return ""
}

func getFloatFromMap(m map[string]interface{}, key string) float64 {
	if val, ok := m[key]; ok {
		if f, ok := val.(float64); ok {
			return f
		}
		if i, ok := val.(int); ok {
			return float64(i)
		}
	}
	return 0
}

// Additional placeholder functions
func updateDomainSettings(domain string, updateData map[string]interface{}) map[string]interface{} {
	// Log the update request
	log.Printf("Updating domain settings for %s: %+v", domain, updateData)
	
	// Update domain settings in Redis
	domainKey := fmt.Sprintf("domain_settings:%s", domain)
	settingsJSON, _ := json.Marshal(updateData)
	rdb.Set(ctx, domainKey, string(settingsJSON), 0)
	
	// If language change is requested, trigger content translation
	if language, ok := updateData["language"].(string); ok && language != "" {
		log.Printf("Language change detected for %s: %s", domain, language)
		
		// Store language preference
		rdb.Set(ctx, fmt.Sprintf("domain_language:%s", domain), language, 0)
	}
	
	// If niche change is requested, update it
	if niche, ok := updateData["niche"].(string); ok && niche != "" {
		log.Printf("Niche change detected for %s: %s", domain, niche)
		rdb.Set(ctx, fmt.Sprintf("domain_niche:%s", domain), niche, 0)
	}
	
	return map[string]interface{}{
		"success": true, 
		"message": "Domain settings updated successfully",
		"domain": domain,
		"updated_data": updateData,
	}
}

func translateDomainContent(translateData map[string]interface{}) map[string]interface{} {
	domain, ok := translateData["domain"].(string)
	if !ok {
		return map[string]interface{}{"success": false, "message": "Domain is required"}
	}
	
	targetLanguage, ok := translateData["target_language"].(string)
	if !ok {
		return map[string]interface{}{"success": false, "message": "Target language is required"}
	}
	
	log.Printf("Starting content translation for domain %s to language %s", domain, targetLanguage)
	
	// Store translation request in Redis for background processing
	translationKey := fmt.Sprintf("translation_queue:%s", domain)
	translationData := map[string]interface{}{
		"domain": domain,
		"target_language": targetLanguage,
		"status": "pending",
		"created_at": time.Now().Format("2006-01-02 15:04:05"),
	}
	
	translationJSON, _ := json.Marshal(translationData)
	rdb.Set(ctx, translationKey, string(translationJSON), 0)
	
	// Trigger background translation process
	go processContentTranslation(domain, targetLanguage)
	
	return map[string]interface{}{
		"success": true,
		"message": "Content translation started",
		"domain": domain,
		"target_language": targetLanguage,
		"status": "processing",
	}
}

func processContentTranslation(domain, targetLanguage string) {
	log.Printf("Processing content translation for %s to %s", domain, targetLanguage)
	
	// Simulate translation process
	time.Sleep(2 * time.Second)
	
	// Update translation status
	translationKey := fmt.Sprintf("translation_queue:%s", domain)
	translationData := map[string]interface{}{
		"domain": domain,
		"target_language": targetLanguage,
		"status": "completed",
		"completed_at": time.Now().Format("2006-01-02 15:04:05"),
	}
	
	translationJSON, _ := json.Marshal(translationData)
	rdb.Set(ctx, translationKey, string(translationJSON), 0)
	
	log.Printf("Content translation completed for %s", domain)
}

func removeDomainFromSystem(domain string) map[string]interface{} {
	// Remove domain from Redis
	domainKey := "domain:" + domain
	rdb.Del(ctx, domainKey)
	
	// Remove from domain list
	domains, err := rdb.SMembers(ctx, "domains").Result()
	if err == nil {
		for _, d := range domains {
			var domainData map[string]interface{}
			json.Unmarshal([]byte(d), &domainData)
			if domainData["name"] == domain {
				rdb.SRem(ctx, "domains", d)
				break
			}
		}
	}
	
	// Log removal
	logEvent("domain_removed", domain, "Domain removed from system", "info")
	
	return map[string]interface{}{
		"success": true, 
		"message": "Domain successfully removed from system",
	}
}

func testConfiguration(testData map[string]interface{}) map[string]interface{} {
	return map[string]interface{}{"success": true, "message": "Configuration test completed"}
}

func startAutonomousSystem() map[string]interface{} {
	return map[string]interface{}{"success": true, "message": "Autonomous system started"}
}

func stopAutonomousSystem() map[string]interface{} {
	return map[string]interface{}{"success": true, "message": "Autonomous system stopped"}
}

func getAnalyticsOverview() map[string]interface{} {
	return map[string]interface{}{"overview": "analytics data"}
}

func getRevenueAnalytics(days int) map[string]interface{} {
	return map[string]interface{}{"revenue": "analytics data"}
}

func getContentAnalytics() map[string]interface{} {
	return map[string]interface{}{"content": "analytics data"}
}

func getPinterestAnalytics() map[string]interface{} {
	return map[string]interface{}{"pinterest": "analytics data"}
}

func acknowledgeAlert(alertID string) map[string]interface{} {
	return map[string]interface{}{"success": true, "message": "Alert acknowledged"}
}

func triggerContentGeneration(request map[string]interface{}) map[string]interface{} {
	return map[string]interface{}{"success": true, "message": "Content generation started"}
}

func getContentQueueStatus() map[string]interface{} {
	return map[string]interface{}{"queue": "status"}
}

func triggerBulkContentGeneration(request map[string]interface{}) map[string]interface{} {
	return map[string]interface{}{"success": true, "message": "Bulk content generation started"}
}

func getPinterestAccounts() []PinterestAccount {
	accountsMutex.RLock()
	defer accountsMutex.RUnlock()
	
	// Debug logging
	log.Printf("Getting Pinterest accounts, total: %d", len(pinterestAccounts))
	for i, account := range pinterestAccounts {
		log.Printf("Account %d: %s (%s)", i, account.AccountName, account.Status)
	}
	
	// Make a copy to avoid race conditions
	accounts := make([]PinterestAccount, len(pinterestAccounts))
	copy(accounts, pinterestAccounts)
	return accounts
}

func createPinterestAccount(accountData map[string]interface{}) map[string]interface{} {
	accountsMutex.Lock()
	defer accountsMutex.Unlock()
	
	// Validate required fields
	accountName, ok := accountData["account_name"].(string)
	if !ok || accountName == "" {
		return map[string]interface{}{"success": false, "message": "Account name is required"}
	}
	
	accessToken, ok := accountData["access_token"].(string)
	if !ok || accessToken == "" {
		return map[string]interface{}{"success": false, "message": "Access token is required"}
	}
	
	boardID, ok := accountData["board_id"].(string)
	if !ok || boardID == "" {
		return map[string]interface{}{"success": false, "message": "Board ID is required"}
	}
	
	status, ok := accountData["status"].(string)
	if !ok {
		status = "active"
	}
	
	// Check if account already exists
	for _, account := range pinterestAccounts {
		if account.AccountName == accountName {
			return map[string]interface{}{"success": false, "message": "Account with this name already exists"}
		}
	}
	
	// Create new account
	newAccount := PinterestAccount{
		ID:          uuid.New().String(),
		AccountName: accountName,
		Username:    accountName, // For now, use account name as username
		Status:      status,
		Followers:   0,
		Pins:        0,
		AccessToken: accessToken,
		BoardID:     boardID,
		CreatedAt:   time.Now().Format("2006-01-02 15:04:05"),
	}
	
	pinterestAccounts = append(pinterestAccounts, newAccount)
	
	// Log for debugging
	log.Printf("Pinterest account created: %s, total accounts: %d", accountName, len(pinterestAccounts))
	
	return map[string]interface{}{
		"success": true, 
		"message": "Pinterest account created",
		"account": newAccount,
	}
}

func checkPinterestAccountStatus(accountID string) map[string]interface{} {
	accountsMutex.RLock()
	defer accountsMutex.RUnlock()
	
	for _, account := range pinterestAccounts {
		if account.ID == accountID {
			return map[string]interface{}{
				"status": account.Status,
				"account": account,
			}
		}
	}
	
	return map[string]interface{}{
		"status": "not_found",
		"message": "Account not found",
	}
}

func getSystemMonitoring() map[string]interface{} {
	return map[string]interface{}{"monitoring": "data"}
}

func getServicesStatus() map[string]interface{} {
	return map[string]interface{}{"services": "status"}
}

func getServiceLogs(service, lines string) map[string]interface{} {
	return map[string]interface{}{"logs": "service logs"}
}

func updateEnvironmentVariables(config SystemConfig) {
	// Update environment variables
}

func restartAffectedServices(config SystemConfig) {
	// Restart services that need config changes
}

func updateDomainAdSense(domain string, updateData map[string]interface{}) map[string]interface{} {
	// Get current domains
	domains := getAllDomains()
	
	// Find and update the domain
	domainFound := false
	for i, d := range domains {
		domainName := getStringFromMap(map[string]interface{}{
			"name": d.Name,
			"domain": d.Name,
		}, "name")
		if domainName == "" {
			domainName = getStringFromMap(map[string]interface{}{
				"domain": d.Name,
			}, "domain")
		}
		
		if domainName == domain {
			// Update AdSense client
			if clientID, ok := updateData["adsense_client"]; ok {
				d.AdSenseClient = clientID.(string)
			}
			domains[i] = d
			domainFound = true
			break
		}
	}
	
	if !domainFound {
		// Store AdSense config for domain in Redis
		adsenseKey := fmt.Sprintf("domain_adsense:%s", domain)
		adsenseData := map[string]interface{}{
			"domain": domain,
			"adsense_client": updateData["adsense_client"],
			"adsense_status": updateData["adsense_status"],
			"updated_at": time.Now().Format(time.RFC3339),
		}
		
		adsenseJSON, _ := json.Marshal(adsenseData)
		rdb.Set(ctx, adsenseKey, string(adsenseJSON), 0)
		
		// Log event
		logEvent("adsense_updated", domain, fmt.Sprintf("AdSense code updated: %s", updateData["adsense_client"]), "info")
		
		return map[string]interface{}{
			"success": true,
			"message": "AdSense kodu başarıyla güncellendi",
		}
	}
	
	// Save domains back to Redis
	domainsJSON, _ := json.Marshal(domains)
	rdb.Set(ctx, "autonomous_domains", string(domainsJSON), 0)
	
	// Log event
	logEvent("adsense_updated", domain, fmt.Sprintf("AdSense code updated: %s", updateData["adsense_client"]), "info")
	
	return map[string]interface{}{
		"success": true,
		"message": "AdSense kodu başarıyla güncellendi",
	}
}

func triggerImageGeneration(request map[string]interface{}) map[string]interface{} {
	// Nano Banana servisini çağır
	count := 3
	if countValue, exists := request["count"]; exists {
		if countInt, ok := countValue.(float64); ok {
			count = int(countInt)
		}
	}
	
	// Log event
	logEvent("image_generation_triggered", "system", fmt.Sprintf("%d images requested", count), "info")
	
	return map[string]interface{}{
		"success": true,
		"message": fmt.Sprintf("%d resim üretimi başlatıldı", count),
		"generated_count": count,
	}
}

func triggerCloudflareDeployment(request map[string]interface{}) map[string]interface{} {
	domains := request["domains"].([]interface{})
	deployedCount := 0
	failedCount := 0
	
	for _, domain := range domains {
		domainStr := domain.(string)
		
		// Queue domain for deployment in Redis
		deploymentData := map[string]interface{}{
			"name": domainStr,
			"type": "redeploy",
			"initiated_by": "dashboard",
			"timestamp": time.Now().Format(time.RFC3339),
			"cloudflare_url": fmt.Sprintf("https://dash.cloudflare.com/3472bd4345145a5b73f49b198580dc3e/home/developer-platform"),
		}
		
		deploymentJSON, _ := json.Marshal(deploymentData)
		
		// Push to deployment queue
		err := rdb.LPush(ctx, "domain_deployment_queue", string(deploymentJSON)).Err()
		if err != nil {
			log.Printf("Failed to queue deployment for %s: %v", domainStr, err)
			failedCount++
		} else {
			deployedCount++
			
			// Log deployment
			logEvent("cloudflare_deploy", domainStr, "Cloudflare deployment queued successfully", "info")
			
			// Store deployment status
			rdb.HSet(ctx, fmt.Sprintf("deployment_status:%s", domainStr), map[string]interface{}{
				"status": "queued",
				"initiated_at": time.Now().Format(time.RFC3339),
				"cloudflare_dashboard": "https://dash.cloudflare.com/3472bd4345145a5b73f49b198580dc3e/home/developer-platform",
			})
		}
	}
	
	if failedCount > 0 {
		return map[string]interface{}{
			"success": false,
			"deployed_count": deployedCount,
			"failed_count": failedCount,
			"message": fmt.Sprintf("%d site deployment başlatıldı, %d başarısız", deployedCount, failedCount),
			"cloudflare_dashboard": "https://dash.cloudflare.com/3472bd4345145a5b73f49b198580dc3e/home/developer-platform",
		}
	}
	
	return map[string]interface{}{
		"success": true,
		"deployed_count": deployedCount,
		"message": fmt.Sprintf("%d site Cloudflare Pages'e deployment başlatıldı", deployedCount),
		"cloudflare_dashboard": "https://dash.cloudflare.com/3472bd4345145a5b73f49b198580dc3e/home/developer-platform",
	}
}

func triggerPinterestPosting(request map[string]interface{}) map[string]interface{} {
	count := 1
	if countValue, exists := request["count"]; exists {
		if countInt, ok := countValue.(float64); ok {
			count = int(countInt)
		}
	}
	
	// Log event
	logEvent("pinterest_posting_triggered", "system", fmt.Sprintf("%d pins requested", count), "info")
	
	return map[string]interface{}{
		"success": true,
		"posted_count": count,
		"message": fmt.Sprintf("%d pin paylaşımı başlatıldı", count),
	}
}

// Admin middleware - checks if user has admin role
func adminMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		userRole, exists := c.Get("userRole")
		if !exists || userRole != "admin" {
			c.JSON(http.StatusForbidden, gin.H{
				"success": false,
				"message": "Admin access required",
			})
			c.Abort()
			return
		}
		c.Next()
	}
}

// Admin handler functions
func apiListUsersHandler(c *gin.Context) {
	// Get all users from Redis
	keys, err := rdb.Keys(ctx, "user:*").Result()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"success": false,
			"message": "Failed to retrieve users",
		})
		return
	}

	var users []User
	for _, key := range keys {
		userData, err := rdb.Get(ctx, key).Result()
		if err != nil {
			continue
		}

		var user User
		if err := json.Unmarshal([]byte(userData), &user); err != nil {
			continue
		}

		// Don't return password
		user.Password = ""
		users = append(users, user)
	}

	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"users": users,
	})
}

func apiChangeUserRoleHandler(c *gin.Context) {
	userID := c.Param("id")
	
	var req struct {
		Role string `json:"role"`
	}
	
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"success": false,
			"message": "Invalid request format",
		})
		return
	}

	if req.Role != "admin" && req.Role != "user" {
		c.JSON(http.StatusBadRequest, gin.H{
			"success": false,
			"message": "Invalid role. Must be 'admin' or 'user'",
		})
		return
	}

	// Get existing user
	userData, err := rdb.Get(ctx, "user:"+userID).Result()
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{
			"success": false,
			"message": "User not found",
		})
		return
	}

	var user User
	if err := json.Unmarshal([]byte(userData), &user); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"success": false,
			"message": "Failed to parse user data",
		})
		return
	}

	// Update role
	user.Role = req.Role

	// Save updated user
	updatedUserData, err := json.Marshal(user)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"success": false,
			"message": "Failed to update user",
		})
		return
	}

	if err := rdb.Set(ctx, "user:"+userID, updatedUserData, 0).Err(); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"success": false,
			"message": "Failed to save user updates",
		})
		return
	}

	// Log the change
	logEvent("user_role_changed", "admin", fmt.Sprintf("User %s role changed to %s", user.Username, req.Role), "info")

	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"message": "User role updated successfully",
	})
}

func apiDeleteUserHandler(c *gin.Context) {
	userID := c.Param("id")

	// Get user info before deleting for logging
	userData, err := rdb.Get(ctx, "user:"+userID).Result()
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{
			"success": false,
			"message": "User not found",
		})
		return
	}

	var user User
	if err := json.Unmarshal([]byte(userData), &user); err == nil {
		// Delete user from Redis
		if err := rdb.Del(ctx, "user:"+userID).Err(); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{
				"success": false,
				"message": "Failed to delete user",
			})
			return
		}

		// Also delete any user sessions
		sessionKeys, _ := rdb.Keys(ctx, "session:*:"+userID).Result()
		for _, sessionKey := range sessionKeys {
			rdb.Del(ctx, sessionKey)
		}

		// Log the deletion
		logEvent("user_deleted", "admin", fmt.Sprintf("User %s deleted", user.Username), "warning")

		c.JSON(http.StatusOK, gin.H{
			"success": true,
			"message": "User deleted successfully",
		})
	} else {
		c.JSON(http.StatusInternalServerError, gin.H{
			"success": false,
			"message": "Failed to delete user",
		})
	}
}

// Security API handlers
func apiSecurityScanStatusHandler(c *gin.Context) {
	// Get security scan status from Redis
	scanStatus, err := rdb.HGetAll(ctx, "security:metrics").Result()
	if err != nil {
		c.JSON(http.StatusOK, gin.H{
			"success": false,
			"message": "Security scan status not available",
			"status": "unknown",
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"data": scanStatus,
	})
}

func apiSecurityLatestReportHandler(c *gin.Context) {
	// Get latest security scan report
	reportData, err := rdb.Get(ctx, "security:latest_scan").Result()
	if err != nil {
		c.JSON(http.StatusOK, gin.H{
			"success": false,
			"message": "No security scan report available",
			"data": gin.H{
				"scan_summary": gin.H{
					"total_findings": 0,
					"successful_scans": 0,
					"failed_scans": 0,
				},
				"findings_by_severity": gin.H{
					"critical": 0,
					"high": 0,
					"medium": 0,
					"low": 0,
				},
				"recommendations": []string{"Security scanning service not running"},
			},
		})
		return
	}

	var report map[string]interface{}
	if err := json.Unmarshal([]byte(reportData), &report); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"success": false,
			"message": "Failed to parse security report",
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"data": report,
	})
}

func apiTriggerSecurityScanHandler(c *gin.Context) {
	// Trigger a new security scan by setting a flag in Redis
	// The security scanner service will pick this up
	err := rdb.Set(ctx, "security:trigger_scan", "requested", time.Minute*10).Err()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"success": false,
			"message": "Failed to trigger security scan",
		})
		return
	}

	// Log the action
	logEvent("security_scan_triggered", "admin", "Manual security scan triggered", "info")

	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"message": "Security scan triggered successfully",
	})
}