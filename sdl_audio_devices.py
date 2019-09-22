import sys
stdout = sys.stdout
sys.stdout = None
import pygame
sys.stdout = stdout

import pygame._sdl2 as sdl2

pygame.init()

for i in range(sdl2.get_num_audio_devices(0)):
    device_name = sdl2.get_audio_device_name(i, 0).decode('utf-8')
    print(f"Device #{i+1}: {device_name}")