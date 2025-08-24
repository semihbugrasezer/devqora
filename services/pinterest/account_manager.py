# /srv/auto-adsense/services/pinterest/account_manager.py
import os
import json
import time
import redis
import requests
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

class AccountStatus(Enum):
    ACTIVE = "active"
    SHADOW_BANNED = "shadow_banned"
    SUSPENDED = "suspended"
    RATE_LIMITED = "rate_limited"
    NEEDS_VERIFICATION = "needs_verification"
    DISABLED = "disabled"

@dataclass
class PinterestAccount:
    id: str
    username: str
    email: str
    password: str
    access_token: str
    refresh_token: str
    status: AccountStatus
    created_at: datetime
    last_used: datetime
    daily_pins: int
    total_pins: int
    followers: int
    boards: List[Dict[str, str]]
    domain_assignment: str  # "hing.me" or "playu.co"
    proxy: Optional[str] = None
    user_agent: Optional[str] = None
    cookies: Optional[Dict] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "password": self.password,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat(),
            "daily_pins": self.daily_pins,
            "total_pins": self.total_pins,
            "followers": self.followers,
            "boards": self.boards,
            "domain_assignment": self.domain_assignment,
            "proxy": self.proxy,
            "user_agent": self.user_agent,
            "cookies": self.cookies
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PinterestAccount':
        return cls(
            id=data["id"],
            username=data["username"],
            email=data["email"],
            password=data["password"],
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            status=AccountStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_used=datetime.fromisoformat(data["last_used"]),
            daily_pins=data["daily_pins"],
            total_pins=data["total_pins"],
            followers=data["followers"],
            boards=data["boards"],
            domain_assignment=data["domain_assignment"],
            proxy=data.get("proxy"),
            user_agent=data.get("user_agent"),
            cookies=data.get("cookies")
        )

class PinterestAccountManager:
    """Pinterest Multi-Account Manager with Shadow Ban Detection"""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            decode_responses=True
        )
        
        # Pinterest API credentials
        self.pinterest_app_id = os.getenv("PINTEREST_APP_ID")
        self.pinterest_app_secret = os.getenv("PINTEREST_APP_SECRET")
        
        # Account creation settings
        self.proxy_list = self.load_proxy_list()
        self.user_agents = self.load_user_agents()
        
        # Domain assignments
        self.domain_accounts = {
            "hing.me": [],
            "playu.co": []
        }
        
        self.load_accounts()
        
        self.log_info("Pinterest Account Manager initialized")
    
    def load_proxy_list(self) -> List[str]:
        """Load proxy list for account creation"""
        proxy_file = os.getenv("PROXY_LIST_FILE", "/srv/auto-adsense/config/proxies.txt")
        proxies = []
        
        try:
            if os.path.exists(proxy_file):
                with open(proxy_file, 'r') as f:
                    proxies = [line.strip() for line in f if line.strip()]
            else:
                # Default proxies (you should replace with real ones)
                proxies = [
                    "http://user:pass@proxy1.example.com:8080",
                    "http://user:pass@proxy2.example.com:8080",
                    "http://user:pass@proxy3.example.com:8080"
                ]
        except Exception as e:
            self.log_error(f"Failed to load proxies: {e}")
        
        return proxies
    
    def load_user_agents(self) -> List[str]:
        """Load realistic user agents"""
        return [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
    
    def load_accounts(self):
        """Load all Pinterest accounts from Redis"""
        try:
            accounts_data = self.redis_client.get("pinterest_accounts")
            if accounts_data:
                accounts_list = json.loads(accounts_data)
                
                for account_data in accounts_list:
                    account = PinterestAccount.from_dict(account_data)
                    domain = account.domain_assignment
                    
                    if domain in self.domain_accounts:
                        self.domain_accounts[domain].append(account)
                
                self.log_info(f"Loaded {len(accounts_list)} Pinterest accounts")
            else:
                self.log_info("No existing Pinterest accounts found")
                
        except Exception as e:
            self.log_error(f"Failed to load accounts: {e}")
    
    def save_accounts(self):
        """Save all accounts to Redis"""
        try:
            all_accounts = []
            for domain_accounts in self.domain_accounts.values():
                all_accounts.extend([acc.to_dict() for acc in domain_accounts])
            
            self.redis_client.set("pinterest_accounts", json.dumps(all_accounts))
            self.log_info(f"Saved {len(all_accounts)} Pinterest accounts")
            
        except Exception as e:
            self.log_error(f"Failed to save accounts: {e}")
    
    def create_new_account(self, domain: str, proxy: str = None) -> Optional[PinterestAccount]:
        """Create a new Pinterest account"""
        try:
            # Generate account details
            account_id = f"pinterest_{int(time.time())}_{random.randint(1000, 9999)}"
            username = self.generate_username(domain)
            email = self.generate_email(username)
            password = self.generate_password()
            
            # Select proxy and user agent
            if not proxy:
                proxy = random.choice(self.proxy_list) if self.proxy_list else None
            user_agent = random.choice(self.user_agents)
            
            self.log_info(f"Creating new Pinterest account: {username}")
            
            # Create account via Pinterest API or automation
            creation_result = self.register_pinterest_account(
                username=username,
                email=email,
                password=password,
                proxy=proxy,
                user_agent=user_agent
            )
            
            if not creation_result["success"]:
                self.log_error(f"Account creation failed: {creation_result['error']}")
                return None
            
            # Get access tokens
            auth_result = self.authenticate_account(email, password, proxy, user_agent)
            if not auth_result["success"]:
                self.log_error(f"Account authentication failed: {auth_result['error']}")
                return None
            
            # Create account object
            account = PinterestAccount(
                id=account_id,
                username=username,
                email=email,
                password=password,
                access_token=auth_result["access_token"],
                refresh_token=auth_result["refresh_token"],
                status=AccountStatus.ACTIVE,
                created_at=datetime.now(),
                last_used=datetime.now(),
                daily_pins=0,
                total_pins=0,
                followers=0,
                boards=[],
                domain_assignment=domain,
                proxy=proxy,
                user_agent=user_agent,
                cookies=auth_result.get("cookies")
            )
            
            # Create initial boards
            self.create_initial_boards(account)
            
            # Add to domain accounts
            self.domain_accounts[domain].append(account)
            self.save_accounts()
            
            # Log creation
            self.log_account_creation(account)
            
            self.log_info(f"Successfully created new Pinterest account: {username}")
            return account
            
        except Exception as e:
            self.log_error(f"Error creating new account: {e}")
            return None
    
    def register_pinterest_account(self, username: str, email: str, password: str, proxy: str, user_agent: str) -> Dict[str, Any]:
        """Register account with Pinterest (automation or API)"""
        try:
            session = requests.Session()
            
            if proxy:
                session.proxies = {"http": proxy, "https": proxy}
            
            session.headers.update({"User-Agent": user_agent})
            
            # Pinterest signup endpoint
            signup_url = "https://www.pinterest.com/resource/UserRegisterResource/create/"
            
            signup_data = {
                "source_url": "/",
                "data": json.dumps({
                    "email": email,
                    "password": password,
                    "username": username,
                    "first_name": username.split("_")[0].capitalize(),
                    "last_name": "",
                    "age": random.randint(25, 45),
                    "country": "US",
                    "language": "en"
                })
            }
            
            # Add CSRF and other required headers
            csrf_response = session.get("https://www.pinterest.com/")
            csrf_token = self.extract_csrf_token(csrf_response.text)
            
            session.headers.update({
                "X-CSRFToken": csrf_token,
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://www.pinterest.com/"
            })
            
            response = session.post(signup_url, data=signup_data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("resource_response", {}).get("data"):
                    return {"success": True, "account_data": result}
                else:
                    return {"success": False, "error": "Registration failed"}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def authenticate_account(self, email: str, password: str, proxy: str, user_agent: str) -> Dict[str, Any]:
        """Authenticate and get access tokens"""
        try:
            # Pinterest OAuth flow or direct login
            session = requests.Session()
            
            if proxy:
                session.proxies = {"http": proxy, "https": proxy}
            
            session.headers.update({"User-Agent": user_agent})
            
            # Login to get tokens
            login_url = "https://www.pinterest.com/resource/UserSessionResource/create/"
            
            login_data = {
                "source_url": "/login/",
                "data": json.dumps({
                    "username_or_email": email,
                    "password": password
                })
            }
            
            response = session.post(login_url, data=login_data)
            
            if response.status_code == 200:
                # Extract tokens from response
                cookies = session.cookies.get_dict()
                
                # Get API access token (if available)
                access_token = self.extract_access_token(response.text, cookies)
                
                return {
                    "success": True,
                    "access_token": access_token or "manual_session",
                    "refresh_token": "manual_refresh",
                    "cookies": cookies
                }
            else:
                return {"success": False, "error": f"Login failed: {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_initial_boards(self, account: PinterestAccount):
        """Create initial boards for the account"""
        try:
            board_templates = {
                "hing.me": [
                    {"name": "Investment Tips", "description": "Smart investment strategies and tips"},
                    {"name": "Financial Planning", "description": "Personal finance and planning advice"},
                    {"name": "Money Management", "description": "Tips for managing your money wisely"},
                    {"name": "Crypto Guide", "description": "Cryptocurrency investment guides"}
                ],
                "playu.co": [
                    {"name": "Gaming Setup", "description": "Best gaming setups and equipment"},
                    {"name": "PC Builds", "description": "Custom PC building guides"},
                    {"name": "Gaming Reviews", "description": "Game and hardware reviews"},
                    {"name": "Streaming Tips", "description": "Tips for game streaming"}
                ]
            }
            
            domain = account.domain_assignment
            boards_to_create = board_templates.get(domain, board_templates["hing.me"])
            
            created_boards = []
            
            for board_template in boards_to_create:
                board_result = self.create_board(account, board_template)
                if board_result["success"]:
                    created_boards.append({
                        "id": board_result["board_id"],
                        "name": board_template["name"],
                        "description": board_template["description"]
                    })
                
                # Rate limiting
                time.sleep(random.randint(5, 15))
            
            account.boards = created_boards
            self.log_info(f"Created {len(created_boards)} boards for {account.username}")
            
        except Exception as e:
            self.log_error(f"Failed to create initial boards: {e}")
    
    def create_board(self, account: PinterestAccount, board_data: Dict[str, str]) -> Dict[str, Any]:
        """Create a single board"""
        try:
            # Pinterest board creation API call
            session = requests.Session()
            
            if account.proxy:
                session.proxies = {"http": account.proxy, "https": account.proxy}
            
            session.headers.update({
                "User-Agent": account.user_agent,
                "Authorization": f"Bearer {account.access_token}"
            })
            
            create_url = "https://api.pinterest.com/v5/boards"
            
            board_payload = {
                "name": board_data["name"],
                "description": board_data["description"],
                "privacy": "PUBLIC"
            }
            
            response = session.post(create_url, json=board_payload)
            
            if response.status_code == 201:
                board_info = response.json()
                return {
                    "success": True,
                    "board_id": board_info["id"],
                    "board_data": board_info
                }
            else:
                return {"success": False, "error": f"Board creation failed: {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def detect_shadow_ban(self, account: PinterestAccount) -> bool:
        """Detect if account is shadow banned"""
        try:
            # Multiple shadow ban detection methods
            
            # 1. Check engagement rates
            if self.check_engagement_drop(account):
                return True
            
            # 2. Check if pins appear in search
            if not self.check_pin_visibility(account):
                return True
            
            # 3. Check API response patterns
            if self.check_api_restrictions(account):
                return True
            
            # 4. Check follower interaction
            if not self.check_follower_engagement(account):
                return True
            
            return False
            
        except Exception as e:
            self.log_error(f"Shadow ban detection error: {e}")
            return False
    
    def check_engagement_drop(self, account: PinterestAccount) -> bool:
        """Check for sudden engagement drop"""
        try:
            # Get recent pin performance
            recent_pins = self.get_recent_pins_performance(account)
            
            if len(recent_pins) < 5:
                return False
            
            # Calculate average engagement
            recent_avg = sum(pin["engagement"] for pin in recent_pins[:5]) / 5
            older_avg = sum(pin["engagement"] for pin in recent_pins[5:10]) / 5 if len(recent_pins) >= 10 else recent_avg
            
            # If engagement dropped by more than 70%
            if recent_avg < (older_avg * 0.3):
                self.log_warning(f"Engagement drop detected for {account.username}: {recent_avg} vs {older_avg}")
                return True
            
            return False
            
        except Exception as e:
            self.log_error(f"Engagement check error: {e}")
            return False
    
    def get_active_account(self, domain: str) -> Optional[PinterestAccount]:
        """Get an active account for the domain"""
        domain_accounts = self.domain_accounts.get(domain, [])
        
        # Filter active accounts
        active_accounts = [
            acc for acc in domain_accounts 
            if acc.status == AccountStatus.ACTIVE
        ]
        
        if not active_accounts:
            self.log_warning(f"No active accounts for {domain}, creating new one")
            new_account = self.create_new_account(domain)
            return new_account
        
        # Select account with lowest daily usage
        selected_account = min(active_accounts, key=lambda x: x.daily_pins)
        
        # Check if account is shadow banned
        if self.detect_shadow_ban(selected_account):
            self.log_warning(f"Shadow ban detected for {selected_account.username}")
            selected_account.status = AccountStatus.SHADOW_BANNED
            self.save_accounts()
            
            # Try to get another account
            return self.get_active_account(domain)
        
        return selected_account
    
    def rotate_accounts(self):
        """Daily account rotation and maintenance"""
        try:
            current_time = datetime.now()
            
            for domain, accounts in self.domain_accounts.items():
                for account in accounts:
                    # Reset daily counters
                    if current_time.date() > account.last_used.date():
                        account.daily_pins = 0
                    
                    # Check account health
                    if account.status == AccountStatus.ACTIVE:
                        if self.detect_shadow_ban(account):
                            account.status = AccountStatus.SHADOW_BANNED
                            self.log_warning(f"Account {account.username} marked as shadow banned")
                            
                            # Create replacement account
                            self.create_new_account(domain)
                    
                    # Refresh tokens if needed
                    if self.should_refresh_tokens(account):
                        self.refresh_account_tokens(account)
            
            self.save_accounts()
            self.log_info("Account rotation completed")
            
        except Exception as e:
            self.log_error(f"Account rotation error: {e}")
    
    def generate_username(self, domain: str) -> str:
        """Generate realistic username"""
        prefixes = {
            "hing.me": ["money", "invest", "finance", "wealth", "smart", "profit"],
            "playu.co": ["game", "play", "tech", "setup", "pro", "epic"]
        }
        
        suffixes = ["guide", "tips", "master", "expert", "hub", "zone", "plus"]
        numbers = random.randint(100, 999)
        
        prefix = random.choice(prefixes.get(domain, prefixes["hing.me"]))
        suffix = random.choice(suffixes)
        
        return f"{prefix}_{suffix}_{numbers}"
    
    def generate_email(self, username: str) -> str:
        """Generate email for account"""
        domains = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com"]
        domain = random.choice(domains)
        return f"{username}@{domain}"
    
    def generate_password(self) -> str:
        """Generate secure password"""
        import string
        
        chars = string.ascii_letters + string.digits + "!@#$%"
        return ''.join(random.choice(chars) for _ in range(12))
    
    def extract_csrf_token(self, html: str) -> str:
        """Extract CSRF token from HTML"""
        import re
        
        match = re.search(r'"csrfToken":"([^"]+)"', html)
        return match.group(1) if match else ""
    
    def extract_access_token(self, response_text: str, cookies: Dict) -> Optional[str]:
        """Extract access token from response"""
        # Implementation depends on Pinterest's response format
        return None
    
    def log_account_creation(self, account: PinterestAccount):
        """Log account creation event"""
        event = {
            "event": "account_created",
            "account_id": account.id,
            "username": account.username,
            "domain": account.domain_assignment,
            "timestamp": datetime.now().isoformat()
        }
        
        self.redis_client.lpush("account_events", json.dumps(event))
        self.redis_client.ltrim("account_events", 0, 999)
    
    def log_info(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] ACCOUNT-MANAGER: {message}")
    
    def log_warning(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] ACCOUNT-MANAGER WARNING: {message}")
    
    def log_error(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] ACCOUNT-MANAGER ERROR: {message}")

# Additional helper methods would be implemented here
# (check_pin_visibility, check_api_restrictions, etc.)

def main():
    """Test Pinterest Account Manager"""
    try:
        manager = PinterestAccountManager()
        
        print("🔧 Pinterest Account Manager Test")
        
        # Test account creation
        new_account = manager.create_new_account("hing.me")
        if new_account:
            print(f"✅ Created account: {new_account.username}")
        
        # Test getting active account
        active_account = manager.get_active_account("hing.me")
        if active_account:
            print(f"✅ Active account: {active_account.username}")
        
        # Test shadow ban detection
        if manager.detect_shadow_ban(active_account):
            print("⚠️  Shadow ban detected")
        else:
            print("✅ Account appears healthy")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    main()
