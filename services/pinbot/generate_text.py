import random

def draft_description(keyword: str) -> str:
    templates = [
        f"{keyword} hakkında hızlı ve pratik bir rehber hazırladık. Detaylar blogda.",
        f"{keyword} konusunda en etkili yöntemleri derledik. Tam liste içerikte.",
        f"{keyword} ile ilgili sık yapılan hatalar ve çözümlerini topladık."
    ]
    return random.choice(templates)

def pick_hashtags(keyword: str):
    base = keyword.lower().replace(" ","")
    return [f"#{base}", "#guide", "#howto"]
