from moviepy.editor import ImageClip, CompositeVideoClip
from PIL import Image, ImageDraw
import numpy as np

# Create a new image with a green background (representing the football field)
def create_frame(frame_number):
    img = Image.new('RGB', (800, 600), color=(0, 128, 0))  # Green background
    draw = ImageDraw.Draw(img)

    # Draw the boy
    boy_x = 100 + frame_number * 5  # Move the boy to the right
    boy_y = 300
    boy_radius = 20
    draw.ellipse([(boy_x, boy_y), (boy_x + boy_radius*2, boy_y + boy_radius*2)], fill=(255, 0, 0))  # Red circle

    # Draw the football
    ball_x = boy_x + boy_radius + 10
    ball_y = boy_y
    ball_radius = 10
    draw.ellipse([(ball_x, ball_y), (ball_x + ball_radius*2, ball_y + ball_radius*2)], fill=(0, 0, 255))  # Blue circle

    # Draw the leg kicking the ball
    leg_x = boy_x + boy_radius
    leg_y = boy_y + boy_radius
    leg_length = 50
    draw.line([(leg_x, leg_y), (leg_x, leg_y + leg_length)], fill=(0, 0, 0), width=5)

    # Save the frame as a file
    img.save(f'frame_{frame_number}.png')

# Create 100 frames
for i in range(100):
    create_frame(i)

# Load the frames into MoviePy
frames = [ImageClip(f'frame_{i}.png').set_duration(0.1) for i in range(100)]

# Create a video clip from the frames
video = CompositeVideoClip(frames)

# Write the video to a file
video.write_videofile('boy_kicking_football.mp4', fps=24)