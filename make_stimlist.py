#!/usr/bin/env python

from random import shuffle
from sys import argv, exit
from os import makedirs
from csv import reader
from shutil import copy
from glob import glob


def main(kern_file, prac_file, target_dir):
    codes = read_codes(kern_file, prac_file)
    
    # Set up item lists
    shuffle(codes)
    E_I_items = codes[:28]
    EI_I_items = codes[28:56]
    EI_items = codes[56:84]
    I_items = E_I_items + EI_I_items
    shuffle(I_items)
    

    # assign day1 to categories
    day1_dir = target_dir + '/day1/'
    makedirs(day1_dir)

    write_cond(day1_dir + 'codes-E.csv', E_I_items, 'E')
    write_cond(day1_dir + 'codes-EI.csv', EI_I_items, 'EI')

    for day1_file in glob('subj_template/day1/*.yaml'):
        copy(day1_file, day1_dir)

    # day 2
    day2_dir = target_dir + '/day2/'
    makedirs(day2_dir)


    # make different order from initial E block
    write_cond(day2_dir + 'codes-I1.csv', I_items[:28], 'I')
    write_cond(day2_dir + 'codes-I2.csv', I_items[28:56], 'I')
    write_cond(day2_dir + 'codes-EI.csv', EI_items, 'EI')

    for day2_file in glob('subj_template/day2/*.yaml'):
        copy(day2_file, day2_dir)

    # Now do our tests
    test_dir = target_dir + '/test/'
    makedirs(test_dir)

    # Need to re-shuffle to get new order from study
    shuffle(codes)
    for i in range(4):
        write_cond(test_dir + 'codes-EM%d.csv' % (i+1), codes[i*32:(i+1)*32], 'EM')

    for test_file in glob('subj_template/test/*.yaml'):
        copy(test_file, test_dir)

def read_codes(kern_file, prac_file):
    kerns_in = reader(open(kern_file))
    # Skip the header
    kerns_in.next()

    # codes = [line.split(',', 1)[0] for line in kerns_in]
    codes = [items[0] for items in kerns_in]

    # Get rid of our practice items
    practice_codes = open(prac_file).readlines()
    for c in practice_codes:
        codes.remove(c.strip())

    return codes

def write_cond(fname, codes, cond):
    code_header = 'Item.code,Condition\n'
    cond = ',%s\n' % cond
    codes_E = open(fname, 'w')
    codes_E.write(code_header)
    codes_E.writelines([code + cond for code in codes])
    codes_E.close()

if __name__ == '__main__':
    if len(argv) != 2:
        print "usage: ./make_stimlist.py <base_dir>"
        exit(1)

    main('shorter-kernels.csv', 'practice-ranney-codes.txt', argv[1])
