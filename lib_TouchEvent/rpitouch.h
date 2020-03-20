/*****************************************************************************
 * 
 * Touch event class for raspberry pi with lcd
 * Created by Zong-Sheng Wang 
 * @ 2017/10/23
 * 
 * Usage:
 *  1. #include "rpitouch.h"
 *  2. init: 
 *      WZS::RPiTouch touch; 
 * 		or 
 * 		WZS::RPiTouch* ptouch = new WZS::RPiTouch(); // need delete operation 
 *  3. update:
 *     3.1 touch.UpdateTouchEvent(); // to update current touch status
 * 	   3.2 touch.GetTouchStatus();  // get current touch status like 
 * 									//   TOUCH_NONE, TOUCH_DOWN, TOUCH_UP
 *       eg: if( touch.GetTouchStatus() == TOUCH_UP ){
 *				int x = touch.GetX(); // obtain x of the touching position
 *				int y = touch.GetY(); // obtain y of the touching position
 *           }
 * Update:
 *  2017/11/15  1. Add GetCursorPosition() to obtain the cursor position which
 *              is the touching position of screen when touch event occured.
 * 	            Recommand you to use GetX(), GetY() interface for obtaining 
 *				touching position, cause GetCursorPosition() has already be 
 *				invoked in UpdateTouchEvent().  
 * 				2. Add GetWindowSize() to obtain the resolution of window
 * Notice:
 *   The LibX11.so library is required, it's defaultly located 
 *	 at '/usr/lib/arm-linux-gnueabihf/'
 *
****************************************************************************/

#ifndef RPITOUCH_H
#define RPITOUCH_H

#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <linux/input.h>
#include <X11/Xlib.h>

#define MOUSEFILE "/dev/input/mouse0"

#define	TOUCH_NONE 0
#define TOUCH_DOWN 1
#define	TOUCH_UP 2

namespace WZS{
	
class RPiTouch
{
	public:
		RPiTouch()
		{
			if((fileno_ = open(MOUSEFILE, O_RDONLY|O_NONBLOCK)) == -1){
				exit(EXIT_FAILURE);
			}
			ptr_ = (unsigned char*)&inputevt_;
			touch_event_ = TOUCH_NONE;
			
			x_display_ = XOpenDisplay(":0");
			if(x_display_ == NULL) {
				exit(EXIT_FAILURE);	
			}
			
			GetWindowSize(&win_width_, &win_height_);
		}
		
		~RPiTouch()
		{
			XCloseDisplay(x_display_);
			close(fileno_);
		}
		
		void UpdateTouchEvent()
		{
			int x, y;
			read(fileno_, &inputevt_, sizeof(struct input_event));
			if( (ptr_[0] & 0x07) == 1 ){
				//if( ptr_[0] == 9 ){
				GetCursorPosition(&x, &y);
				if(x_ != x && y_!= y){
					x_ = x; y_ = y;
					touch_event_ = TOUCH_DOWN;
				}
			}else{
				if(touch_event_ == TOUCH_DOWN) 	{
					GetCursorPosition(&x_, &y_);
					touch_event_ = TOUCH_UP;
				}else{
					 touch_event_ = TOUCH_NONE;
				}
			}
			
		}
		
		int GetTouchStatus() { return touch_event_; }		
		int GetX() { return x_; }
		int GetY() { return y_; }
		int GetWindowWidth() { return win_width_; }
		int GetWindowHeight() { return win_height_; }
		
		void GetCursorPosition(int* x, int* y)
		{
			XQueryPointer(x_display_, DefaultRootWindow(x_display_),
				&x_root_window_, &x_root_window_,
				x, y, x, y, &x_mask_);
			//printf("at x=%d, y=%d\n", *x, *y);
		}
		
		void GetWindowSize(int *width, int *height)
		{
			Window root_win = DefaultRootWindow(x_display_);
			XWindowAttributes xwAttr;
			XGetWindowAttributes(x_display_, root_win, &xwAttr);
			*width = xwAttr.width;
			*height = xwAttr.height;
		}
		
	private:
		int fileno_;
		struct input_event inputevt_;
		unsigned char *ptr_;
		int touch_event_;
		int x_, y_;
		// for X11
		Window x_root_window_;
		unsigned int x_mask_;		
		Display *x_display_;
		int win_width_, win_height_;
		
};

};

#endif
