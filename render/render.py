import pyglet
import numpy as np


class GLRenderer:
    def __init__(self, width=400, height=400, pixel_size=4, title='Driving'):
        self.width = width
        self.height = height
        self.pixel_size = pixel_size
        self.scaled_width = int(self.width * self.pixel_size)
        self.scaled_height = int(self.height * self.pixel_size)
        self.window = pyglet.window.Window(width=self.scaled_width, height=self.scaled_height, caption=title, vsync=True)
        self.frame = None
        self.sprite = None

        @self.window.event
        def on_draw():
            self.window.clear()
            if self.frame is None:
                return
            if self.sprite is not None:
                self.sprite.draw()

    def _create_texture(self):
        pass

    def update_frame(self, frame: np.ndarray):
        if frame is None:
            return
        if frame.shape[0] != self.height or frame.shape[1] != self.width:
            frame = np.flipud(frame)
            frame = np.ascontiguousarray(np.transpose(frame, (1, 0, 2)))
            frame = np.resize(frame, (self.height, self.width, frame.shape[2]))
        frame = frame.astype(np.uint8)
        if self.pixel_size != 1:
            frame = np.repeat(frame, self.pixel_size, axis=0)
            frame = np.repeat(frame, self.pixel_size, axis=1)
        if frame.shape[2] == 3:
            fmt = 'RGB'
            bytes_per_pixel = 3
        else:
            fmt = 'RGBA'
            bytes_per_pixel = 4
        data_bytes = frame.tobytes()
        image = pyglet.image.ImageData(self.scaled_width, self.scaled_height, fmt, data_bytes, pitch= -self.scaled_width * bytes_per_pixel)
        self.sprite = pyglet.sprite.Sprite(image, x=0, y=0)
        self.frame = frame

    def run_once(self):
        pyglet.clock.tick()
        self.window.dispatch_events()
        self.window.dispatch_event('on_draw')
        self.window.flip()
