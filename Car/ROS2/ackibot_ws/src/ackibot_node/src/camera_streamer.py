import gi
import cv2
import numpy as np
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
from line_detection import detect_lines_logic

Gst.init(None)

# 1. Pipeline za kameru: Koristimo libcamerasrc za Pi 5
# Postavljamo format na BGR za jednostavnu konverziju u OpenCV
capture_pipe = Gst.parse_launch(
    "libcamerasrc ! video/x-raw,width=640,height=480,format=BGR ! appsink name=mysink emit-signals=True sync=False"
)

# 2. Pipeline za striming (ostaje isti)
stream_pipe = Gst.parse_launch(
    "appsrc name=mysrc caps=video/x-raw,format=BGR,width=640,height=480,framerate=30/1 ! "
    "videoconvert ! openh264enc bitrate=2000000 ! h264parse ! rtph264pay ! udpsink host=10.1.151.8 port=5600"
)

sink = capture_pipe.get_by_name("mysink")
appsrc = stream_pipe.get_by_name("mysrc")

def on_new_sample(sink):
    print("DObijen Frame")
    sample = sink.emit("pull-sample")
    buf = sample.get_buffer()
    
    result, mapinfo = buf.map(Gst.MapFlags.READ)
    # Kreiramo BGR matricu direktno iz bafera
    frame = np.ndarray((480, 640, 3), buffer=mapinfo.data, dtype=np.uint8)
    
    # TVOJA LOGIKA
    processed_frame, offset = detect_lines_logic(frame)
    
    buf.unmap(mapinfo)
    
    # Slanje obrađene slike na mrežu
    new_buf = Gst.Buffer.new_allocate(None, processed_frame.nbytes, None)
    new_buf.fill(0, processed_frame.tobytes())
    appsrc.emit("push-buffer", new_buf)
    
    return Gst.FlowReturn.OK

sink.connect("new-sample", on_new_sample)

print("Sistem pokrenut. Čekam frejmove...")
capture_pipe.set_state(Gst.State.PLAYING)
stream_pipe.set_state(Gst.State.PLAYING)

try:
    GLib.MainLoop().run()
except KeyboardInterrupt:
    print("Gašenje...")
    capture_pipe.set_state(Gst.State.NULL)
    stream_pipe.set_state(Gst.State.NULL)