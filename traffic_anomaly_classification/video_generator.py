import os
import cv2
import numpy as np
import random

def create_road_background(width, height):
    # Dark asphalt background
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:] = (40, 40, 40)
    
    # Sidewalks
    cv2.rectangle(frame, (0, 0), (60, height), (100, 100, 100), -1)
    cv2.rectangle(frame, (width - 60, 0), (width, height), (100, 100, 100), -1)
    
    # Road shoulders lines
    cv2.line(frame, (60, 0), (60, height), (255, 255, 255), 2)
    cv2.line(frame, (width - 60, 0), (width - 60, height), (255, 255, 255), 2)
    
    # Lane separators (3 lanes)
    lane_width = (width - 120) // 3
    for i in range(1, 3):
        x = 60 + i * lane_width
        # Dashed lines
        for y in range(0, height, 40):
            cv2.line(frame, (x, y), (x, y + 20), (200, 200, 200), 2)
            
    return frame

def draw_car(frame, x, y, w, h, color, angle=0):
    # Draw a rotated rectangle for the car
    rect = ((x, y), (w, h), angle)
    box = cv2.boxPoints(rect)
    box = np.intp(box)
    cv2.drawContours(frame, [box], 0, color, -1)
    
    # Draw headlights or details
    # For simplicity, draw windshield
    windshield_color = (240, 240, 240)
    if angle == 0 or angle == 180:
        cv2.rectangle(frame, (int(x - w/3), int(y - h/4)), (int(x + w/3), int(y - h/10)), windshield_color, -1)
    else:
        cv2.rectangle(frame, (int(x - w/4), int(y - h/3)), (int(x - h/10), int(y + h/3)), windshield_color, -1)

def generate_normal_traffic(output_path, width=640, height=480, duration=3, fps=10):
    num_frames = duration * fps
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    lane_width = (width - 120) // 3
    lane_centers = [60 + lane_width // 2 + i * lane_width for i in range(3)]
    
    # Define cars: [x, y, speed, color]
    cars = [
        {"lane": 0, "y": 0, "speed": 12, "color": (50, 200, 50)},    # Green car in lane 0
        {"lane": 1, "y": 150, "speed": 10, "color": (200, 150, 50)}, # Blue car in lane 1
        {"lane": 2, "y": 300, "speed": 14, "color": (50, 180, 200)}  # Cyan car in lane 2
    ]
    
    for f in range(num_frames):
        frame = create_road_background(width, height)
        
        # Draw cars
        for car in cars:
            x = lane_centers[car["lane"]]
            car["y"] = (car["y"] + car["speed"]) % height
            draw_car(frame, x, car["y"], 30, 50, car["color"])
            
        cv2.putText(frame, "Normal Trafik Akisi", (80, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        out.write(frame)
        
    out.release()

def generate_accident(output_path, width=640, height=480, duration=3, fps=10):
    num_frames = duration * fps
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    lane_width = (width - 120) // 3
    lane_centers = [60 + lane_width // 2 + i * lane_width for i in range(3)]
    
    # Car A starts from top lane 0, moves down
    # Car B starts from bottom lane 1, moves up
    y_a = 50
    y_b = height - 50
    collision_frame = num_frames // 2 # Frame 15
    collision_y = height // 2
    
    speed_a = (collision_y - y_a) / collision_frame
    speed_b = (y_b - collision_y) / collision_frame
    
    # Particle class for debris simulation
    particles = []
    
    for f in range(num_frames):
        frame = create_road_background(width, height)
        
        if f < collision_frame:
            # Cars approaching
            y_a += speed_a
            y_b -= speed_b
            
            # Car B decides to swerve lane erratically, leading to a head-on collision
            # Let's slide Car B's X coordinate towards lane 0
            t = f / collision_frame
            x_a = lane_centers[0]
            x_b = lane_centers[1] - t * (lane_centers[1] - lane_centers[0])
            
            draw_car(frame, x_a, y_a, 30, 50, (50, 180, 200)) # Cyan car
            draw_car(frame, x_b, y_b, 30, 50, (50, 50, 250)) # Red car
        else:
            # Collision has happened
            # Cars stop and rotate slightly
            x_a = lane_centers[0]
            x_b = lane_centers[0] - 10
            
            draw_car(frame, x_a, collision_y - 15, 30, 50, (50, 180, 200), angle=15)
            draw_car(frame, x_b, collision_y + 15, 30, 50, (50, 50, 250), angle=-25)
            
            # Generate sparks/debris
            if f == collision_frame:
                for _ in range(30):
                    particles.append({
                        "x": float(lane_centers[0]),
                        "y": float(collision_y),
                        "vx": random.uniform(-15, 15),
                        "vy": random.uniform(-15, 15),
                        "size": random.randint(2, 6),
                        "color": random.choice([(0, 120, 255), (0, 230, 255), (100, 100, 100)]) # Yellow, orange, gray
                    })
            
            # Update and draw particles
            for p in particles:
                p["x"] += p["vx"]
                p["y"] += p["vy"]
                p["vx"] *= 0.85
                p["vy"] *= 0.85
                cv2.circle(frame, (int(p["x"]), int(p["y"])), p["size"], p["color"], -1)
                
            # Flash "CRASH" overlay
            if f % 2 == 0:
                cv2.rectangle(frame, (0, 0), (width, height), (0, 0, 255), 5)
                
            cv2.putText(frame, "KAZA ALGILANDI!", (80, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            
        out.write(frame)
        
    out.release()

def generate_fight(output_path, width=640, height=480, duration=3, fps=10):
    num_frames = duration * fps
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # Sidewalk coordinates
    x_base = 35
    y_base = height // 2
    
    # Two people (colored dots/small boxes)
    p1_x, p1_y = x_base, y_base - 20
    p2_x, p2_y = x_base, y_base + 20
    
    for f in range(num_frames):
        frame = create_road_background(width, height)
        
        # High-energy erratic motion simulating a fight
        if f > 5:
            # Erratic movements
            p1_x += random.randint(-8, 8)
            p1_y += random.randint(-8, 8)
            p2_x += random.randint(-8, 8)
            p2_y += random.randint(-8, 8)
            
            # Keep them on the sidewalk or near road edge
            p1_x = max(10, min(80, p1_x))
            p1_y = max(100, min(height - 100, p1_y))
            p2_x = max(10, min(80, p2_x))
            p2_y = max(100, min(height - 100, p2_y))
            
            # Draw collision/struggle indicators (red circles flashing)
            if f % 2 == 0:
                cv2.circle(frame, (int((p1_x + p2_x)/2), int((p1_y + p2_y)/2)), 30, (0, 0, 255), 1)
        else:
            # Standing normally
            pass
            
        # Draw "people" (represented by orange/red rectangles)
        cv2.rectangle(frame, (p1_x - 8, p1_y - 8), (p1_x + 8, p1_y + 8), (50, 100, 255), -1) # Blue shirt person
        cv2.rectangle(frame, (p2_x - 8, p2_y - 8), (p2_x + 8, p2_y + 8), (50, 50, 250), -1)  # Red shirt person
        
        cv2.putText(frame, "Kavga / Fiziksel Mudahale", (80, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        out.write(frame)
        
    out.release()

def generate_obstacle(output_path, width=640, height=480, duration=3, fps=10):
    num_frames = duration * fps
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    lane_width = (width - 120) // 3
    lane_centers = [60 + lane_width // 2 + i * lane_width for i in range(3)]
    
    # Static obstacle in lane 1 (center)
    obs_x = lane_centers[1]
    obs_y = height // 2
    
    # Car coming down in lane 1
    car_y = 0
    car_x = lane_centers[1]
    
    for f in range(num_frames):
        frame = create_road_background(width, height)
        
        # Draw obstacle (yellow/black striped box)
        obs_w, obs_h = 35, 35
        cv2.rectangle(frame, (obs_x - obs_w//2, obs_y - obs_h//2), (obs_x + obs_w//2, obs_y + obs_h//2), (0, 190, 240), -1)
        # Add diagonal stripes
        for k in range(-15, 20, 8):
            cv2.line(frame, (obs_x - obs_w//2 + k, obs_y - obs_h//2), (obs_x - obs_w//2 + k + 10, obs_y + obs_h//2), (0, 0, 0), 3)
            
        # Car movement
        car_y += 12
        if car_y > height:
            car_y = 0
            car_x = lane_centers[1]
            
        # Avoidance logic
        # Swerve to lane 0 (left) starting when car gets close (e.g. y = obs_y - 120)
        if obs_y - 150 < car_y < obs_y + 80:
            # Smoothly transition to lane 0
            t = (car_y - (obs_y - 150)) / 100 # Transition variable 0 to 1
            t = min(1.0, max(0.0, t))
            car_x = lane_centers[1] - t * (lane_centers[1] - lane_centers[0])
        elif car_y >= obs_y + 80:
            # Transition back to center lane
            t = (car_y - (obs_y + 80)) / 100
            t = min(1.0, max(0.0, t))
            car_x = lane_centers[0] + t * (lane_centers[1] - lane_centers[0])
            
        # Draw car
        angle = 0
        if obs_y - 150 < car_y < obs_y:
            angle = -15  # Leaning left
        elif obs_y < car_y < obs_y + 80:
            angle = 15   # Leaning back right
            
        draw_car(frame, int(car_x), int(car_y), 30, 50, (50, 200, 50), angle=angle)
        
        cv2.putText(frame, "Yolda Engel / Duran Arac", (80, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)
        out.write(frame)
        
    out.release()

def generate_violation(output_path, width=640, height=480, duration=3, fps=10):
    num_frames = duration * fps
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # Custom intersection background
    # Let's draw a horizontal intersection
    def create_intersection():
        frame = create_road_background(width, height)
        # Add horizontal road in the middle
        cv2.rectangle(frame, (0, height//2 - 60), (width, height//2 + 60), (40, 40, 40), -1)
        cv2.line(frame, (0, height//2 - 60), (width, height//2 - 60), (255, 255, 255), 2)
        cv2.line(frame, (0, height//2 + 60), (width, height//2 + 60), (255, 255, 255), 2)
        
        # Red stop line for vertical lanes
        cv2.line(frame, (60, height//2 - 70), (width - 60, height//2 - 70), (0, 0, 255), 4)
        
        # Traffic light symbol (Red)
        cv2.circle(frame, (width - 40, height//2 - 90), 12, (20, 20, 20), -1)
        cv2.circle(frame, (width - 40, height//2 - 90), 10, (0, 0, 255), -1) # Red light on
        
        return frame
        
    lane_width = (width - 120) // 3
    lane_centers = [60 + lane_width // 2 + i * lane_width for i in range(3)]
    
    # Car approaching intersection from top, lane 1
    car_y = 20
    car_x = lane_centers[1]
    speed = 18 # High speed, running the light
    
    for f in range(num_frames):
        frame = create_intersection()
        
        car_y += speed
        draw_car(frame, car_x, car_y, 30, 50, (50, 50, 250)) # Red car violating
        
        # If car crosses stop line (height//2 - 70)
        if car_y > height//2 - 70:
            # Highlight warning
            if f % 2 == 0:
                cv2.putText(frame, "KIRMIZI ISIK IHLALI!", (width//2 - 150, height//2), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 3)
                # Red flash border
                cv2.rectangle(frame, (0, 0), (width, height), (0, 0, 255), 3)
                
        cv2.putText(frame, "Kural Ihlali Algilama", (80, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        out.write(frame)
        
    out.release()

def generate_all_samples(target_dir):
    os.makedirs(target_dir, exist_ok=True)
    
    print("Sentetik videolar uretiliyor...")
    
    generate_normal_traffic(os.path.join(target_dir, "normal.mp4"))
    print("- normal.mp4 uretildi.")
    
    generate_accident(os.path.join(target_dir, "accident.mp4"))
    print("- accident.mp4 uretildi.")
    
    generate_fight(os.path.join(target_dir, "fight.mp4"))
    print("- fight.mp4 uretildi.")
    
    generate_obstacle(os.path.join(target_dir, "obstacle.mp4"))
    print("- obstacle.mp4 uretildi.")
    
    generate_violation(os.path.join(target_dir, "violation.mp4"))
    print("- violation.mp4 uretildi.")
    
    print("Tum sentetik videolar basariyla uretildi.")

if __name__ == "__main__":
    generate_all_samples("./static/samples")
