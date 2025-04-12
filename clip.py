from moviepy.editor import VideoFileClip

input_video = "/Users/raghavansrinivas/Downloads/videoplayback.mp4"
output_video = "/Users/raghavansrinivas/Downloads/output_clip.mp4"

clip = VideoFileClip(input_video).subclip(10, 20)
clip.write_videofile(output_video)
