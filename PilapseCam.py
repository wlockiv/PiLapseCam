#!~/VEnvironments/PiLapseCam/

# TODO
 # 1.) TRIGGER CAMERA.............................DONE
 # 2.) MOVE IMAGES FROM SD CARD TO SPEC. FOLDER...DONE
 # 2.) RENAME FILE TO DATE/TIME USING EXIF........DONE
 # 3.) INTERVELOMETER ACCOUNTING FOR DAYS, HOURS..DONE
 # 4.) GRAPHICAL USER INTERFACE
 #      a - SETTINGS FROM JSON
 # 5.) EMAIL ERROR REPORTING
 # 6.) GUIDE CAMERA CONTROLS
 # 7.) UPLOAD TO CLOUD STORAGE


# Imports from Python 3.4 Native Library
from __future__ import print_function
import time
import logging
import os
import pathlib
import subprocess
import sys
import shutil
import json

# Imports from PyPi Libraries
import gphoto2 as gp
import exifread
from apscheduler.schedulers.background import BlockingScheduler
from Timelapse import Timelapse

##Calculated. Don't touch these!
tl = Timelapse()
                    
#
# Kill the 'gvfsd-gphoto2' process
#
def killgphoto():
    p = subprocess.Popen(['killall', 'gvfsd-gphoto2'])
    out, err = p.communicate()

#
# Convert the exifread object to a readable date and time
#
def exif_todatetimestr(exifread):
    #Convert the IfDTag to string then
    #chop off text before '=' and after '@'
    result = repr(exifread).split('=', 1)[-1].split('@',)[0]
    #Strip of leading and tailing spaces then
    #replace spaces with underscores and colons with dashes
    #within the date portion
    result = result.strip().replace(' ', '_').replace(':', '-', 2)
    return result

#
# Convert the exifread object to a readable date
#
def exif_todatestr(exifread):
    #Convert the IfDTag to string then
    #chop off text '=' and before, '@' and after
    result = repr(exifread).split('=', 1)[-1].split('@',)[0]
    #Strip of leading and tailing spaces then
    #chop off last space and after
    result = result.strip().split(' ',)[0]
    #Strip spaces one final time
    #Replace colons with dashes
    result = result.strip().replace(':', '-')
    return result

#
# Capture Sequence
#
def captureandsave(camera, context):

    #Capture Action
    cameraCapturePath = gp.check_result(gp.gp_camera_capture(
        camera, gp.GP_CAPTURE_IMAGE, context))

    #Making Target Save photo_local_root Dir
    target = os.path.join(tl.getConfig('photo_local_root'), cameraCapturePath.name)
    
    #Grab Captured Image Extension
    captureFileExtension = pathlib.Path(cameraCapturePath.name).suffix
    
    #GP_FILE_TYPE_NORMAL for JPEG; GP_FILE_TYPE_RAW for RAW
    if (tl.getConfig('FILE_TYPE') == 'RAW'):
        camera_file = gp.check_result(gp.gp_camera_file_get(
                camera, cameraCapturePath.folder, cameraCapturePath.name,
                gp.GP_FILE_TYPE_RAW, context))
    elif (tl.getConfig('FILE_TYPE') == 'JPEG'):
        camera_file = gp.check_result(gp.gp_camera_file_get(
                camera, cameraCapturePath.folder, cameraCapturePath.name,
                gp.GP_FILE_TYPE_NORMAL, context))
                
    gp.check_result(gp.gp_file_save(camera_file, target))
    gp.check_result(gp.gp_camera_file_delete(camera, cameraCapturePath.folder,
                                      cameraCapturePath.name, context))

    #Rename Based on EXIF Data
    target_open = open(target, 'rb')
    exif_tags = exifread.process_file(target_open, \
                                 stop_tag='EXIF DateTimeOriginal')
    for tag in exif_tags.keys():
    #Only Perform Following if tag is Date/Time
        #Change file extension here for RAW/JPEG
        if tag in ('EXIF DateTimeOriginal'):
            file_name = exif_todatetimestr(exif_tags[tag]) + captureFileExtension
            file_dir = os.path.join(tl.getConfig('photo_local_root'), 
                                    exif_todatestr(exif_tags[tag]))

            #Check existence of file_dir, the create it if false
            if not os.path.exists(file_dir):
                os.makedirs(file_dir)

            #Rename and move the captured image then sleep
            shutil.move(target, os.path.join(file_dir, file_name))
            time.sleep(3)

#
# Main Function
#
def main():

    logging.basicConfig(filename='test.log', level=logging.ERROR, \
                    format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')

    #Kill gphoto2
    killgphoto()
    
    
    #Declaring/Calculating variables needed
    scheduler = BlockingScheduler(timezone='US/Central')
    hourbound = tl.getConfig('START_HOUR') + '-' + tl.getConfig('FINISH_HOUR')
    
    
    #Ensure photo_local_root exists
    if not os.path.exists(tl.getConfig('photo_local_root')):
        os.makedirs(tl.getConfig('photo_local_root'))

    #GP2 Log and Camera Setup
    gp.check_result(gp.use_python_logging())
    context = gp.gp_context_new()
    camera = gp.check_result(gp.gp_camera_new())
    gp.check_result(gp.gp_camera_init(camera, context))

    #Adding job to scheduler
    scheduler.add_job(captureandsave, 'cron', args=[camera,context], \
                      day_of_week='mon-sun', second='*/'+str(tl.getConfig('INTERVAL')), \
                      hour=hourbound)
    print('Press Ctrl+{0} to exit'.format( \
          'Break' if os.name == 'nt' else 'C'))

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        pass
        
    #Close Camera
    gp.check_result(gp.gp_camera_exit(camera, context))
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
