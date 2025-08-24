# /srv/auto-adsense/services/pinbot/tailwind_api.py
import os
import json
import time
import requests
from typing import Dict, Any, Optional

class TailwindAPI:
    """Tailwind App API integration for Pinterest posting"""
    
    def __init__(self):
        self.api_key = os.getenv("TAILWIND_API_KEY")
        self.base_url = "https://api.tailwindapp.com/v1"
        self.session = requests.Session()
        
        if self.api_key:
            self.session.headers.update({
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "AutoAdSense/1.0"
            })
    
    def is_configured(self) -> bool:
        """Check if Tailwind API is properly configured"""
        return bool(self.api_key)
    
    def get_boards(self) -> Dict[str, Any]:
        """Get available Pinterest boards from Tailwind"""
        try:
            if not self.is_configured():
                return {"error": "Tailwind API key not configured"}
            
            response = self.session.get(f"{self.base_url}/boards")
            response.raise_for_status()
            
            data = response.json()
            return {
                "success": True,
                "boards": data.get("boards", []),
                "total": len(data.get("boards", []))
            }
            
        except requests.exceptions.RequestException as e:
            return {"error": f"API request failed: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}
    
    def create_pin(self, pin_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create and schedule a Pinterest pin through Tailwind"""
        try:
            if not self.is_configured():
                return {"error": "Tailwind API key not configured"}
            
            # Prepare pin data for Tailwind API
            payload = {
                "pin": {
                    "title": pin_data.get("title", ""),
                    "description": pin_data.get("description", ""),
                    "link": pin_data.get("target_url", ""),
                    "board_id": pin_data.get("board_id"),
                    "image_url": pin_data.get("image_url"),
                    "publish_at": pin_data.get("schedule_time", "now"),
                    "hashtags": pin_data.get("hashtags", [])
                }
            }
            
            # If image is provided as local file, upload it first
            if pin_data.get("image_path"):
                upload_result = self._upload_image(pin_data["image_path"])
                if upload_result.get("success"):
                    payload["pin"]["image_url"] = upload_result["image_url"]
                else:
                    return upload_result
            
            response = self.session.post(f"{self.base_url}/pins", json=payload)
            response.raise_for_status()
            
            data = response.json()
            
            return {
                "success": True,
                "pin_id": data.get("pin", {}).get("id"),
                "scheduled_time": data.get("pin", {}).get("publish_at"),
                "status": "scheduled",
                "tailwind_id": data.get("pin", {}).get("tailwind_id")
            }
            
        except requests.exceptions.RequestException as e:
            return {"error": f"Pin creation failed: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}
    
    def _upload_image(self, image_path: str) -> Dict[str, Any]:
        """Upload image to Tailwind for pin creation"""
        try:
            if not os.path.exists(image_path):
                return {"error": f"Image file not found: {image_path}"}
            
            with open(image_path, 'rb') as img_file:
                files = {'image': img_file}
                response = self.session.post(f"{self.base_url}/images", files=files)
                response.raise_for_status()
                
                data = response.json()
                return {
                    "success": True,
                    "image_url": data.get("image_url"),
                    "image_id": data.get("image_id")
                }
                
        except requests.exceptions.RequestException as e:
            return {"error": f"Image upload failed: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}
    
    def get_pin_stats(self, pin_id: str) -> Dict[str, Any]:
        """Get statistics for a specific pin"""
        try:
            if not self.is_configured():
                return {"error": "Tailwind API key not configured"}
            
            response = self.session.get(f"{self.base_url}/pins/{pin_id}/stats")
            response.raise_for_status()
            
            data = response.json()
            stats = data.get("stats", {})
            
            return {
                "success": True,
                "pin_id": pin_id,
                "impressions": stats.get("impressions", 0),
                "saves": stats.get("saves", 0),
                "clicks": stats.get("clicks", 0),
                "comments": stats.get("comments", 0),
                "updated_at": stats.get("updated_at")
            }
            
        except requests.exceptions.RequestException as e:
            return {"error": f"Stats retrieval failed: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}
    
    def get_account_stats(self) -> Dict[str, Any]:
        """Get overall account statistics"""
        try:
            if not self.is_configured():
                return {"error": "Tailwind API key not configured"}
            
            response = self.session.get(f"{self.base_url}/account/stats")
            response.raise_for_status()
            
            data = response.json()
            stats = data.get("stats", {})
            
            return {
                "success": True,
                "total_pins": stats.get("total_pins", 0),
                "total_impressions": stats.get("total_impressions", 0),
                "total_saves": stats.get("total_saves", 0),
                "total_clicks": stats.get("total_clicks", 0),
                "monthly_views": stats.get("monthly_views", 0),
                "updated_at": stats.get("updated_at")
            }
            
        except requests.exceptions.RequestException as e:
            return {"error": f"Account stats failed: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}
    
    def schedule_pin(self, pin_data: Dict[str, Any], schedule_time: str) -> Dict[str, Any]:
        """Schedule a pin for future posting"""
        pin_data["schedule_time"] = schedule_time
        return self.create_pin(pin_data)
    
    def bulk_schedule_pins(self, pins_data: list, start_time: str, interval_hours: int = 2) -> Dict[str, Any]:
        """Schedule multiple pins with time intervals"""
        results = []
        base_time = time.time()
        
        if start_time != "now":
            # Parse start_time and convert to timestamp
            # For simplicity, assuming ISO format
            pass
        
        for i, pin_data in enumerate(pins_data):
            schedule_timestamp = base_time + (i * interval_hours * 3600)
            schedule_time = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(schedule_timestamp))
            
            result = self.schedule_pin(pin_data, schedule_time)
            results.append({
                "index": i,
                "pin_title": pin_data.get("title", ""),
                "scheduled_time": schedule_time,
                "result": result
            })
            
            # Rate limiting
            time.sleep(1)
        
        return {
            "success": True,
            "scheduled_count": len([r for r in results if r["result"].get("success")]),
            "failed_count": len([r for r in results if not r["result"].get("success")]),
            "results": results
        }

# Usage example and testing function
def test_tailwind_api():
    """Test function for Tailwind API"""
    api = TailwindAPI()
    
    if not api.is_configured():
        print("⚠️  Tailwind API key not configured")
        return False
    
    # Test getting boards
    boards_result = api.get_boards()
    if boards_result.get("success"):
        print(f"✅ Found {boards_result['total']} boards")
        
        # Test creating a pin
        test_pin = {
            "title": "Test Pin from Auto AdSense",
            "description": "Testing our automated Pinterest posting system! 📌 #automation #testing",
            "target_url": "https://hing.me/articles/test",
            "board_id": boards_result["boards"][0]["id"] if boards_result["boards"] else None,
            "image_url": "https://via.placeholder.com/600x900/6366f1/ffffff?text=Test+Pin",
            "hashtags": ["automation", "testing", "adsense"]
        }
        
        pin_result = api.create_pin(test_pin)
        if pin_result.get("success"):
            print(f"✅ Pin created successfully: {pin_result['pin_id']}")
            return True
        else:
            print(f"❌ Pin creation failed: {pin_result.get('error')}")
    else:
        print(f"❌ Failed to get boards: {boards_result.get('error')}")
    
    return False

if __name__ == "__main__":
    test_tailwind_api()
