#!/usr/bin/env python

### Std Lib Imports

from csv import reader
from textwrap import wrap
from os.path import dirname, join

# Installed libs

import yaml
import pygame
from VisionEgg.Text import Text

# Our libs

from cognac.SimpleVisionEgg import SimpleVisionEgg
from cognac.StimController import StimController, Trial, Event, Response

from visionegg_cam_capture import Recording


### Utility function

# TODO: would be nice if this could also handle scientific notation
def format_num(x):
    '''Take a number, put commas for a number in the millions, otherwise write
    "Trillions", "Billions", etc.
    
    x - a STRING of 0-9's'''
    def float_num(x, exponent):
        '''Format a big number to look nice
        
        x: the number
        exponent: e.g. 12 for trillion'''
        units = x[:-exponent]
        if len(units) < 3:
            # Get a few digits after the decimal point
            frac = x[-exponent:(-exponent + 3 - len(units))]
            frac = frac.rstrip('0')
            if len(frac) > 0:
                units = units + '.' + frac

        return units

    if x.lower().find('e') != -1:
        # Get rid of scientific notation
        x = str(int(float(x)))
    elif x.find('.') != -1:
        # This is a reasonable decimal number...
        return x

    if len(x) > 12:
        return float_num(x, 12) + ' Trillion'
    if len(x) > 9:
        return float_num(x, 9) + ' Billion'

    i = 3
    final = x[-i:]
    while i < len(x):
        final = x[-(i+3):-i] + ',' + final
        i += 3

    return final
    


### Presentation Classes

# This seems "wrong," instantiating classes before declaring others but it gets
# the job done!
vision_egg = SimpleVisionEgg()

xlim, ylim = vision_egg.screen.size

std_params = {'anchor': 'center',
              'color': (0,0,0),
              'font_size': 55,
              'on': False}

instruction = Text(text='ESTIMATE', position=(xlim/2, 7 * ylim/8),
                            **std_params)
description = []
for i in range(4):
    description.append(Text(text='Total U.S. population', 
                            position=(xlim/2, (11-i) * ylim/16), **std_params))

value = Text(text='300,000', position=(xlim/2, 3 * ylim/8), 
                      **std_params)

answer = Text(text='<>', position=(xlim/2, ylim/8),
                       **std_params)

vision_egg.set_stimuli([instruction, value, answer] + description)

recording = Recording()

class ReadResponse(Response):
    limit = ('return', 'enter', 'space')

class SurpriseResponse(Response):
    limit = ('1', '2', '3', '[1]', '[2]', '[3]')
    target = answer
    label = 'surprise'

    def __init__(self):
        '''Simply here to avoid calling the superclass __init__'''
        pass

    def record_response(self, t):
        '''Updated to give timing feedback'''
        retval = Response.record_response(self, t)
        # if (not retval) and t - self.ref_time > 2.0:
        #         self.target.set(text="Don't think too hard!", color=(1, 0, 0))

        return retval


class MemoryResponse(SurpriseResponse):
    limit = ('1', '2', '3', '4', '[1]', '[2]', '[3]', '[4]')
    label = 'memory'


class EstimateResponse(Response):
    response = ''
    target = answer
    label = 'estimate'
    start_time = None
    timeout = 5.0

    def __init__(self, timeout=5.0):
        '''Bypass Response.__init__'''

        self.timeout = timeout

    def record_response(self, t):
        """obtain a textual answer typed from the keyboard"""
        responses = pygame.event.get(pygame.KEYDOWN)
        pygame.event.clear()

        if responses:
            key = pygame.key.name(responses[0].key)
            if key in ('return', 'enter'):
                if self.response:
                    self.rt = t - self.ref_time
                    return True
            else:
                if key == 'space':
                    self.response += ' '
                elif key in ('backspace', 'delete'):
                    self.response = self.response[:-1]
                else:
                    # Code our time to start
                    if self.start_time is None:
                        self.start_time = t - self.ref_time

                    if len(key) > 1:
                        self.response += key[1]
                    else:
                        self.response += key

                self.target.set(text = self.response)

        # if self.start_time is None and t - self.ref_time > self.timeout:
        #     self.target.set(text="Don't think too hard!", color=(1, 0, 0))

        return False


class PresentKernel(Trial):
    def __init__(self, condition, value_text, desc_text, fname):
        '''All we need to present a single trial of our experiment

        So far, only integrated recording into 'EI'

        fname :
            the name of the avi where we'll store subject face images
        '''
        # Chunks of stuff that get done in different trials
        def generic_E(desc_stop): 
            return [ Event(instruction, 0.5, 'start_reading', text='ESTIMATE',
                           log={'condition': condition},
                           response=ReadResponse('start_reading')) ] + \
                   self.display_description(desc_text, 'start_reading', 
                                            desc_stop) + \
                   [ Event(answer, 'start_reading', desc_stop, 
                           text='<>', color=(0,0,0), 
                           response=EstimateResponse(timeout=5.0)) ]

        def surprise(surp_start):
            # return [ Event(answer, surp_start, 'surprise', text='<>',
            #               color=(0,0,0), response=SurpriseResponse()),
            return [ Event(instruction, surp_start, 'surprise',
                           text='SURPRISED?', response=SurpriseResponse() )]

        # Now define our actual conditions
        value_text = format_num(value_text)

        if condition == 'I':
            events = [ Event(instruction, 0.5, 'start_reading', text='READ',
                             log={'condition': 'I'},
                             response=ReadResponse('start_reading')),
                       Event(value, 'start_reading', 'surprise', 
                             text=value_text) ] + \
                     self.display_description(desc_text, 
                                              ('start_reading', 2.0), 
                                              'surprise') + \
                     surprise(('start_reading', 2.0))
        elif condition == 'E':
            events = generic_E('estimate')
        elif condition == 'EI':
            # Note that we set the first 'value' to offset after 'surprise' to
            # prevent this from deactivating the second value prompt ('<>')
            # right at 'read_num'
            events = [ Event(recording, 0.0, 'surprise', fname=fname) ] + \
                     generic_E('surprise') + \
                     [ Event(value, ('estimate', 0.5), 'surprise', 
                             text=value_text)] + \
                     surprise(('estimate', 2.5))
        elif condition == 'EM':
            #         [ Event(answer, 'estimate', 'memory', text='<>',
            #                 color=(0,0,0) ),
            events = generic_E('memory') + \
                     [ Event(instruction, 'estimate', 'memory',
                             text='MEMORY?', response=MemoryResponse() ) ]


        Trial.__init__(self, events)

    def display_description(self, desc_text, first_start, stop, line_width=53):
        desc_lines = wrap(desc_text, line_width)
        if len(desc_lines) > 4:
            desc_lines = desc_lines[0:4]
            print "description doesn't wrap to 4 lines:\n***"
            print desc_text, '\n***'
        
        labels = ('read0', 'read1', 'read2', 'read3')
        start_times = (first_start, 'read0', 'read1', 'read2')
        return [Event(desc_stim, first_start, stop, text=line) 
                    for desc_stim, line in zip(description, desc_lines)]


def open_and_check(fname, expected_header):
    csv_iter = reader(open(fname))
    csv_header = csv_iter.next()
    if csv_header != expected_header:
        print "%s header should be: %s" % (fname, expected_header)
        exit(1)

    return csv_iter
                    
def main(yaml_file, kern_file='shorter-kernels.csv'):
    try:
        parms = yaml.load(open(yaml_file))
        base = dirname(yaml_file)
        if not base:
            base = '.'
    except:
        print "Problem with the YAML file!"
        exit(1)

    kernels_in = open_and_check(kern_file, 
                     ['Item.code', 'Value', 'Description', 'Format'] )

    kernels = {}
    for code, value, desc_text, format in kernels_in:
        if format:
            desc_text = '%s [%s]' % (desc_text, format)
        kernels[code] = (value, desc_text)

    order_in = open_and_check(join(base, parms['subj_order_file']), 
                                ['Item.code', 'Condition'])

    trials = []
    for code, cond in order_in:
        value, desc_text = kernels[code]
        fname = join(base, 'trial%02d.avi' % len(trials))
        trials.append( PresentKernel(cond, value, desc_text, fname) )

    stim_control = StimController(trials, vision_egg)
    stim_control.run_trials()

    stim_control.writelog(join(base, parms['log_file']))

if __name__ == '__main__':
    from sys import argv, exit

    if len(argv) != 2:
        print "usage: ./numeric_questions.py <desc_file>.yaml"
        exit(1)

    main(argv[1])
