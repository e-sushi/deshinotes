---
tags: deshi, module
---
# deshi UI
---
the ui system for deshi. 

The interface is based entirely around starting a window, adding items to it, then ending it.
In order to use the interface you must `#include "ui.h"`, located in deshi/core/, where ever you plan to use it.

UI requires you to call it's `Init()` function before any other call.
This initializes all of UI's base [[deshi/deshi ui/deshi UI#Style|styles]] and [[deshi/deshi ui/deshi UI#color|colors]] and makes the base window.

## Window
---
A window is a collection of items with optional decorations placed around them. The interface for starting and ending a window is
```cpp
void Begin(const char* name, UIWindowFlags flags = 0);
void Begin(const char* name, vec2 pos, vec2 dimensions, UIWindowFlags flags = 0);

void End();
```
For example:
```cpp
using namespace UI;

Begin("win", vec2(100,100), vec2(200,300));

End();
```
will result in
![[02-20-2022_20-18-24_suugu.png]]
an empty window with a dark background and borders.
#### Naming
***
A window must be given a unique identifier. Using the same name for 2 windows you want to be different will result in one window containing all the items you tried to place in both.

#### Flags
---
A window may take any combination of these flags
*  UIWindowFlags_NoResize
prevents resizing of the window using it's edges

*  UIWindowFlags_NoMove
prevents movement of the window
* UIWindowFlags_NoBorder
prevents border decorations from being drawn
* UIWindowFlags_NoBackground
prevents background decoration from being drawn
* UIWindowFlags_NoScrollBarX
prevents horizontal scroll bar decoration from being drawn, does not disable scrolling in x direction
* UIWindowFlags_NoScrollBarY
prevents vertical scroll bar decoration from being drawn, does not disable scrolling in x direction
* UIWindowFlags_NoScrollBars
prevents scroll bar decorations from being drawn, does not disable scrolling
* UIWindowFlags_NoScrollX
prevents horizontal scrolling. this also sets UIWindowFlags_NoScrollBarX
* UIWindowFlags_NoScrollY
prevents vertical scrolling. this also sets UIWindowFlags_NoScrollBarY
* UIWindowFlags_NoScroll
prevents all scrolling. this also sets UIWindowFlag_NoScrollBars
* UIWindowFlags_NoFocus
prevents the window from focusing over others when clicked
* UIWindowFlags_FocusOnHover
focuses the window as soon as the mouse cursor moves over it
* UIWindowFlags_DontSetGlobalHoverFlag
prevents the window from setting the global hover flag returned by UI::IsAnyWinHovered

* UIWindowFlags_FitAllElements
auto sizes the window's decorations to fit all items placed in the window. items may be ignored by this flag by using UI::NextItemMinSizeIgnored() directly before it.

* UIWindowFlags_NoInteract
a combination of NoMove, NoResize, No Focus, DontSetGlobalHoverFlag and NoScroll

* UIWindowFlags_Invisible
a combination of NoMove, NoResize, NoBackground and NoFocus
#### Child Windows
---
Any window is capable of having child windows. There are normal child windows and pop out child windows. 
Both behave mostly like a normal window does, with some differences. They also accept all of the same flags a normal window does.
##### Normal child windows 
Normal children are placed into the parent window just like any other [[deshi/deshi ui/deshi UI#item|item]]. 

They are created using the functions
```cpp
void BeginChild(const char* name, vec2 dimensions, UIWindowFlags flags = 0);
void BeginChild(const char* name, vec2 pos, vec2 dimensions, UIWindowFlags flags = 0);
```
and ended using
```cpp
void EndChild();
```

Due to the base window created in `UI::Init()` you dont actually need to explicitly make a parent window to use these.
Example:
```cpp
using namespace UI;
Begin("win", vec2(100,100), vec2(200,300));{
    Text("some text");

    BeginChild("child win", vec2(100,100));{

	    Text("some text inside child window");

    }EndChild(); 

    Text("some more text");
}End();
```
results in 
![[02-20-2022_20-34-31_suugu.png]]
 you may nest child windows as much as you want.

 ##### Pop out child windows
 Pop out child windows are detached from the parent and behaves just like a floating window does, but it's parent window can never draw over it.

 They are created and ended using the functions
 ```cpp
void BeginPopOut(const char* name, vec2 pos, vec2 dimensions, UIWindowFlags flags = 0);
void EndPopOut();
 ```
For example:
```cpp
using namespace UI;

Begin("win", vec2(100,100), vec2(200,300));{
	Text("some text");

	BeginPopOut("child win", vec2(100,100), vec2(100,100));{
		Text("some text in the pop out");
	}EndPopOut();

	Text("some more text");
}End();
```

will result in 
![[02-20-2022_20-45-29_suugu.png]]

 Note that the popout window does not affect items in the parent like normal child windows do.
 Note that the popout window's position is relative to it's parent's position
#### Cursor
---
A UI Window internally tracks a cursor that determines where the next [[deshi/deshi ui/deshi UI#item|item]] is going to be placed. This cursor is controllable using the functions
#TODO-DOCS cursor code and visual example
 
 
## Item
---
An item is anything placed inside of a [[deshi/deshi ui/deshi UI#Window|window]]. 

#### Text
---
The text item iterface is 
```cpp
void Text(const char* text, UITextFlags flags = 0);
void Text(const char* text, vec2 pos, UITextFlags flags = 0);
void Text(const wchar* text, UITextFlags flags = 0);
void Text(const wchar* text, vec2 pos, UITextFlags flags = 0);
void TextF(const char* fmt, ...);
```
The first 2 take a normal ASCII c string, while the following 2 take a unicode c string. `TextF` allows formatting the string like `printf`.
For example:
```cpp
using namespace UI;

Begin("win", vec2(100,100), vec2(200,300));{
	Text("some text");
}End();
```
results in
![[02-20-2022_21-29-46_suugu.png]]
Text wraps on window edges by default
![[02-20-2022_21-28-33_suugu.gif]]

##### Flags
A text item may take any of the following flags

###### UITextFlags_NoWrap
Prevents the default wrapping behavoir.
Ex:
#TODO-DOCS make this gif loop better
![[02-20-2022_21-25-01_suugu.gif]]
##### Color
Text's color can be modified using the `UIStyleCol_Text` flag with `UI::PushColor()`.
For example:
```cpp
using namespace UI;
Begin("win", vec2(100,100), vec2(200,100));{
	PushColor(UIStyleCol_Text, color(0,255,0));
	Text("some text that should be green");
	PopColor();
}End();
```
results in 
![[02-20-2022_21-23-36_suugu.png]]
#NOTE maybe just demonstrate items through the DemoWindow, writing this is too much work :)
## Style
---

## Color
---

