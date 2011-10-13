#!/usr/bin/env python

'''visionegg-cam-capture.py

Even more efficient script to do camera caputre with opencv and display with
visionegg (for ultimate inclusion with my stimulus script). Also capture the
video to file.

Got pygame stuff from this blog:

http://www.jperla.com/blog/post/capturing-frames-from-a-webcam-on-linux
'''

from warnings import warn
# Requires python >= 2.6
import multiprocessing as mp

# PIL might be overkill here, but it's a better "semantic" representation of
# images, you could also use plain numpy
# Note, I'm not using e.g., opencv.adaptors.Ipl2NumPy because the C++ wrappers
# aren't installed by default with homebrew. I really need to consider
# pyopencv! - though apparently it only works with OpenCV <= 2.1, with no plans
# to necessarily update. Willow Garage is comitted to their own C++ wrappers
# as of 2.2
# import Image
import cv
import pygame # VisionEgg depends on this anyway - it's not an extra dependency
from OpenGL import GL
from numpy import flipud
from VisionEgg.Textures import Texture, TextureStimulus

from cognac.SimpleVisionEgg import SimpleVisionEgg 

# highgui is specific to capturing/displaying images
# It doesn't exist on homebrew (2.2?) install, so you just use the direct C
# function calls from the bare cv library
# The C++ import style DOES exist on the 2.1 debian install. So, I'm guessing we
# could figure out a way to make it work on homebrew as well.

# from opencv import highgui 

# Note - the docs refer to e.g., `ReleaseCapture` and `ReleaseVideoWriter`
# functions, but it doesn't see to exist in python. using `del` on the
# allocated structures seems to do the right thing (finalize files, release
# cameras, etc.). In simple scripts, simply exiting will do the right thing (at
# least, it has so far)

class CVCam:
    '''A more user-friendly wrapper around the openCV camera interface'''

    def __init__(self):
        self.camera = cv.CreateCameraCapture(0)
        height = cv.GetCaptureProperty(self.camera, cv.CV_CAP_PROP_FRAME_HEIGHT)
        self.height = int(height)
        width = cv.GetCaptureProperty(self.camera, cv.CV_CAP_PROP_FRAME_WIDTH)
        self.width = int(width)

    def get_image(self):
        im = cv.QueryFrame(self.camera)

        return im

    def conv2array(self, im):
        '''Convert an Ipl to something suitable for PyGame

        I _think_ this used to be available as an "adaptor", but doesn't seem
        available now.

        This is adapted from the opencv 2.1 cookbook
        http://opencv.willowgarage.com/documentation/python/cookbook.html#opencv-to-pygame

        Note - pyopencv doesn't use / need the Mat structure (I think)
        '''
        # height and width are also available as attributes of the image

        # images come off the camera in Ipl format, which need to be converted
        # to Mat before we can share with the outside world
        im_rgb = cv.CreateMat(self.height, self.width, cv.CV_8UC3)
        cv.CvtColor(im, im_rgb, cv.CV_BGR2RGB)
        # Note that flipud is doing double duty, also converting to a proper
        # numpy.array. flipud returns a view when it can, so it's unlikely
        # you'll get more efficient than this.
        arr = flipud(im_rgb)

        return arr 

class CVWriter:
    '''User-friendly wrapper for writing video files
    
    Note that this is currently not working - I'm just capturing the stuff I've
    figured out so far'''

    def __init__(self, fname, size, fps=30, codec='HFYU'):
        '''Straightforward init function
        
        fname :
            I _think_ fname needs to be *.avi
        '''
        # Best so far (sort of working, for at least wonky linux players)

        # 'HFYU' - HuffYUV - reasonable lossless compression?
        # Had strange interlacing problems, vertical stripes, horizontal offset
        # of colors with QuickTime. After setting color flag to '1', had final
        # frame turn out OK. Very weird - pretty sure it's a codec issue.
        # Works on (g)xine, mplayer (via ffmpeg, I assume).

        # My number one choice if I could get it to work better!

        # 'FFV1' - FFMpeg lossless compression - very good apparently
        # Similar problems as with HFYU on the mac, on totem, got an "Internal
        # data stream error", xine doesn't play. Only works with mplayer

        # These also kind of work

        # 'MJPG' - Motion JPEG, probably lossy-compression. 
        # Same banding problem on totem. Also works on (g)xine and mplayer.

        # 'I420' - YUV 4:2:0 colorspace sampling. Again, similar problems to
        # HFYU on totem (bands of video, mostly gray). Works on VLC, gxine, etc.

        # These seem completely unsupported, at least with the FFmpeg backend -
        # they don't yeild an actual writer

        # 'MJP2' - MotionJPEG2000
        # 'PNG1' - CorePNG
        # 'MPNG' - Motion PNG
        # 'DIB ' - RGB(A)
        # 'LAGS' - lagarith, sounds good compared to HuffYUV (fork?)

        self.set_codec(codec) 
        self.writer = cv.CreateVideoWriter(fname, self.codec, fps, size)
        # This is pretty clunky, but so it goes for these python bindings
        if repr(self.writer) == '<VideoWriter (nil)>':
            warn('Failed to initialize VideoWriter using %s' % codec)

    def set_codec(self, codec):
        '''Converts form a more usable string through the strange FOURCC
        
        codec : 
            A 4-character string representing a supported codec. Sadly,
            there seems to be no way to get a list of these codecs. But see
            http://opencv.willowgarage.com/wiki/VideoCodecs
            http://opencv.willowgarage.com/wiki/QuickTimeCodecs
            http://stackoverflow.com/questions/1136989/creating-avi-files-in-opencv/1137034#1137034
            This seems to be a list of codecs supported by ffmpeg, who knows how
            up to date it is!
            http://en.wikipedia.org/wiki/FFmpeg
            http://www.mplayerhq.hu/DOCS/HTML/en/menc-feat-enc-libavcodec.html
        '''
        # We use a relatively underused fact that strings are sequences in
        # python to do char unpacking
        self.codec = cv.FOURCC(*codec)

    def write_im(self, im):
        '''Write an Ipl image from openCV to the opened file'''
        cv.WriteFrame(self.writer, im)




class CameraWindow:
    '''A simple class to set up a pygame window
    
    A general design principle is that ALL openCV code should be encapsulated in
    classes such as the above.`'''

    writer = None

    def __init__(self, fname=None):
        '''Straightforward init

        fname :
            I think this needs to be *.avi
        '''
        # Set camera up first, as this is more likley to fail (I guess)
        self.cv_cam = CVCam()
        im = self.cv_cam.get_image()
        arr = self.cv_cam.conv2array(im)
        self.size = self.cv_cam.width, self.cv_cam.height
        if fname:
            self.writer = CVWriter(fname, self.size)

        # Then, we set up our graphical environment

        # SimpleVisionEgg is a custom set-up class I wrote to avoid boilerplate
        # code duplication. It's a little clunky, sadly.
        self.vision_egg = SimpleVisionEgg()
        screen_center = [x/2.0 for x in self.vision_egg.screen.size]
        tex_stim = TextureStimulus(mipmaps_enabled=False,
                                   texture=Texture(arr),
                                   size=self.size,
                                   # We shouldn't invoke OpenGL texture
                                   # filtering, as we take our texture size
                                   # directly from the camera.
                                   # the other option would be
                                   # GL_NEAREST
                                   texture_min_filter=GL.GL_LINEAR,
                                   position=screen_center,
                                   anchor='center')
        # This gives us programmatic access to the actual video memory (if
        # possible), so it should make things nice and fast. We still seem to be
        # down around 14 fps, though, on the Mac. We're not going to get much
        # faster on this front.
        self.tex_object = tex_stim.parameters.texture.get_texture_object()
        self.vision_egg.set_stimuli([tex_stim])


    def update_image(self, t):
        '''Grab an image from the camera and convert to a pygame.image
        
        I'm using my SimpleVisionEgg system, so I need to discard the time
        parameter `t` that gets passed in'''
        im = self.cv_cam.get_image()
        if self.writer:
            self.writer.write_im(im)
        arr = self.cv_cam.conv2array(im)
        # Note - we use .put_sub_image because we aren't using dimensions that
        # are a power of 2. There's a little more OpenGL magic going on somwhere
        # that I don't know about...
        self.tex_object.put_sub_image(arr)

        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                # For some reason, using VisionEgg we don't exit cleanly and
                # finalize our writer (thus, the movie is corrupted)
                del self.writer
                del self.cv_cam
                self.vision_egg.quit()

    def run(self):
        '''Run forever (until we get a QUIT event)'''
        self.vision_egg.set_functions(update=self.update_image)
        self.vision_egg.go()


class Recording:
    '''A simple class that works kind of like a VisionEgg stimulus, but
    recording from the camera as opposed to showing an image.

    Man would this be a job for Traits!
    '''

    def __init__(self):
        self.on = mp.Event()


    def set(self, on, fname=None):
        '''General purpose, but should just be using 'on' as a key for now'''
        if on:
            self.on.set()
            self.child = mp.Process(target=self.record, args=(on, fname))
            self.child.start()
        else:
            self.on.clear()
            self.child.join()

    def open(self, fname):
        '''Prepare a MovieWriter with fname'''

    def finalize(self):
        del self.writer

    def record(self, on, fname):
        '''Can be run as a separate process to continuously grab frames, while
        allowing the parent process to carry on'''
        print 'creating writer for %s' % fname
        camera = CVCam()
        size = camera.width, camera.height
        writer = CVWriter(fname, size)
        while self.on.is_set():
            im = camera.get_image()
            # arr = self.camera.conv2array(im)
            writer.write_im(im)

        del writer
        del camera



if __name__ == '__main__':
    win = CameraWindow('test.avi')
    win.run()
