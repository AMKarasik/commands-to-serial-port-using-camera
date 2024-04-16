# commands-to-serial-port-using-camera

Program for sending commands to the control unit using the camera. [Link to BMSD brushed DC motor control unit.](https://electroprivod.ru/bdc-driver_bmsd.htm)
Camera detects a circle with a division into black and white sectors, as in the screenshot below. We look at the intersection of the red vertical line and the blue horizontal.
Determine the color of the incoming pixel and start the rotation by sending commands. Each time the black pixel occurs, the rotation speed is automatically switched.

More details about the commands can be found in the BMSD passport.

_**Tools/Packages**_: 
Python 3.10, numpy, serial, cv2.

_Screenshot of the program:_

<a href="https://ibb.co/tmvMLJt"><img src="https://i.ibb.co/7YZJk15/screen.png" alt="screen" border="0"></a>
