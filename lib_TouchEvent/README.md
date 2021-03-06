# Touch Event Library
## rpitouch.h 
rpitouch.h is a library for handling touch event of Raspberry Pi mounted with a touchable LCD on Raspbian OS.

The touchable LCD information is on:
https://www.waveshare.com/wiki/5inch_HDMI_LCD

### Usage:
  1. #include "rpitouch.h"
  2. init:   
    WZS::RPiTouch touch;     
 		or     
 		WZS::RPiTouch* ptouch = new WZS::RPiTouch(); // need delete operation( delete ptouch; ) 
    
  3. update:
  
     3.1 touch.UpdateTouchEvent(); // to update current touch status
     
 	   3.2 touch.GetTouchStatus();  // get current touch status like TOUCH_NONE, TOUCH_DOWN, TOUCH_UP
                  
       eg:
       ```cpp
          if( touch.GetTouchStatus() == TOUCH_UP ) {
              int x = touch.GetX(); // obtain x of the touching position
              int y = touch.GetY(); // obtain y of the touching position
          }
       ```
### Notice:
  The libX11.so library is required to add to the link path. The libX11.so is defaultly located at /usr/lib/arm-linux-gnueabihf/

