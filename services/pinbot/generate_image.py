from PIL import Image, ImageDraw, ImageFont
import os, time

def make_pin_image(text: str, out_path: str, size=(1000,1500)):
    img = Image.new("RGB", size, (255,255,255))
    d = ImageDraw.Draw(img)
    
    try: 
        font = ImageFont.truetype("DejaVuSans.ttf", 56)
    except: 
        font = ImageFont.load_default()
    
    words = text.split()
    lines = []
    line = ""
    
    for w in words:
        if len(line + " " + w) < 22: 
            line += (" " if line else "") + w
        else: 
            lines.append(line)
            line = w
    if line: 
        lines.append(line)
    
    y = 120
    for ln in lines[:9]: 
        d.text((80,y), ln, fill=(0,0,0), font=font)
        y += 80
    
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.save(out_path, "JPEG", quality=90)
    return out_path
