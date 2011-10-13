#!/usr/bin/env python
'''Simple script to run through all kernel text and see what crashes the system'''

from numeric_questions import *

class PresentBareKernel(PresentKernel):
    def __init__(self, code, value_text, desc_text):
        events = self.display_description(desc_text, 0, 
                                          'response', 53) + \
                 [ Event(instruction, 0, 'response', text=code,
                            response=ReadResponse('response')),
                   Event(value, 0, 'response', text=format_num(value_text)) ]
        Trial.__init__(self, events) 
                       
def main(kern_file='shorter-kernels.csv'):
    kernels_in = open_and_check(kern_file, 
                    ['Item.code', 'Value', 'Description', 'Format'])
    
    trials = []
    for code, value, desc_text, format in kernels_in:
        if format:
            desc_text = '%s [%s]' % (desc_text, format)
        trials.append(PresentBareKernel(code, value, desc_text))
        
    stim_control = StimController(trials, vision_egg)
    stim_control.run_trials()
    
if __name__ == '__main__':
    main()
