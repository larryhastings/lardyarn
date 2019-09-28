import pygame


def init_sound(settings):
    print("[INFO] Initializing sound...")

    if pygame.mixer.get_init():
        pygame.mixer.quit()
    try:
        pygame.mixer.pre_init(devicename=settings.get('mixer devicename'))
        pygame.mixer.init()
    except pygame.error as e:
        print(
            "[WARN] Couldn't get exclusive access to sound device! "
            "Sound disabled."
        )
        print("[WARN]", e)

        # call init again with no devicename
        # this will reset back to the default
        # which ALSO won't work, but pygame works better this way.
        pygame.mixer.pre_init(devicename=None)
        pygame.mixer.init()
