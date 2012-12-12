#!/usr/bin/python2.4
#
# Copyright 2011, Google Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#    * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#    * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Check a DSPL dataset for likely import errors."""


__author__ = 'Benjamin Yolken <yolken@google.com>'

import optparse
import os
import shutil
import sys
import tempfile
import time
import zipfile

from dspllib.model import dspl_model_loader
from dspllib.validation import dspl_validation
from dspllib.validation import xml_validation


def LoadOptionsFromFlags(argv):
  """Parse command-line arguments.

  Args:
    argv: The program argument vector (excluding the script name)

  Returns:
    A dictionary with key-value pairs for each of the options
  """
  usage_string = 'python dsplcheck.py [options] [DSPL XML file or zip archive]'

  parser = optparse.OptionParser(usage=usage_string)

  parser.set_defaults(verbose=True)
  parser.add_option('-q', '--quiet',
                    action='store_false', dest='verbose',
                    help='Quiet mode')

  parser.add_option(
      '-l', '--checking_level', dest='checking_level', type='choice',
      choices=['schema_only', 'schema_and_model', 'full'], default='full',
      help='Level of checking to do (default: full)')

  (options, args) = parser.parse_args(args=argv)

  if not len(args) == 1:
    parser.error('An XML file or DSPL zip archive is required')

  return {'verbose': options.verbose,
          'checking_level': options.checking_level,
          'file_path': args[0]}


def GetInputFilePath(input_file_path):
  """Parse the input file path, extracting a zip file if necessary.

  Args:
    input_file_path: String path to dsplcheck input file

  Returns:
    Dictionary containing final XML file path (post-extraction) and directory
    into which zip was extracted (or '' if input was not a zip).
  """
  if zipfile.is_zipfile(input_file_path):
    # Extract files to temporary directory and search for dataset XML
    zip_dir = tempfile.mkdtemp()

    zip_file = zipfile.ZipFile(input_file_path, 'r')
    zip_file.extractall(zip_dir)

    xml_file_paths = []

    for (dirpath, unused_dirnames, filenames) in os.walk(zip_dir):
      for file_name in filenames:
        if file_name[-4:] == '.xml':
          xml_file_paths.append(os.path.join(dirpath, file_name))

    if not xml_file_paths:
      print 'Error: zip does not have any XML files'
      sys.exit(2)
    elif len(xml_file_paths) > 1:
      print 'Error: zip contains multiple XML files'
      sys.exit(2)
    else:
      xml_file_path = xml_file_paths[0]

    zip_file.close()
  else:
    xml_file_path = input_file_path
    zip_dir = ''

  return {'xml_file_path': xml_file_path,
          'zip_dir': zip_dir}


def main(argv):
  """Parse command-line flags and run XML validator.

  Args:
    argv: The program argument vector (excluding the script name)
  """
  start_time = time.time()

  options = LoadOptionsFromFlags(argv)
  file_paths = GetInputFilePath(options['file_path'])

  try:
    xml_file = open(file_paths['xml_file_path'], 'r')
  except IOError as io_error:
    print 'Error opening XML file\n\n%s' % io_error
    sys.exit(2)

  if options['verbose']:
    print '==== Checking XML file against DSPL schema....'

  result = xml_validation.RunValidation(
      xml_file,
      verbose=options['verbose'])

  print result

  if 'validates successfully' not in result:
    # Stop if XML validation not successful
    sys.exit(2)

  if options['checking_level'] != 'schema_only':
    if options['verbose']:
      print '\n==== Parsing DSPL dataset....'

    if options['checking_level'] == 'full':
      full_data_check = True
    else:
      full_data_check = False

    try:
      dataset = dspl_model_loader.LoadDSPLFromFiles(
          file_paths['xml_file_path'], load_all_data=full_data_check)
    except dspl_model_loader.DSPLModelLoaderError as loader_error:
      print 'Error while trying to parse DSPL dataset\n\n%s' % loader_error
      sys.exit(2)

    if options['verbose']:
      print 'Parsing completed.'

      if full_data_check:
        print '\n==== Checking DSPL model and data....'
      else:
        print '\n==== Checking DSPL model....'

    dspl_validator = dspl_validation.DSPLDatasetValidator(
        dataset, full_data_check=full_data_check)

    print dspl_validator.RunValidation(options['verbose'])

  xml_file.close()

  if file_paths['zip_dir']:

    shutil.rmtree(file_paths['zip_dir'])

  if options['verbose']:
    print '\nCompleted in %0.2f seconds' % (time.time() - start_time)


if __name__ == '__main__':
  main(sys.argv[1:])
