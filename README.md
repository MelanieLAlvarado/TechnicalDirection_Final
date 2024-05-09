# Multiple Joint Controller Tool
## Introduction
This Maya tool was developed to aid in the process of creating controllers for a rig with a chain of multiple joints such as a spine, neck, or tail.

## Install
* Download and unzip the plugin to the maya script folder which should appear like this:

<img src=assets/installDirectory.png>

* Drag the install.mel to maya's viewport

## Instructions
### **To Begin using the tool:**
* Open tool by clicking the chain icon on the shelf.

<img src=assets/toolShelf.png>

### **To select the joints in the chain:**
* Select starting joint of the chain (the joint must be the highest in the hierarchy to work).

<img src=assets/selectStartJoint.png>

* Type a keyword shared by all joints in the chain *(The first joint does not require a keyword)*.

* Click the **"Auto Find Joints"** button underneath the keyword to gather the joints.
>Note: there must be at more than 3 joints for the selection to be valid

<img src=assets/gatherJoints.png>

### **The chain will require/produce three controls, and for each control:**

* Select a joint you wish the control to be attached to.

<img src=assets/selectCtrlJoint.png>

* Click the corresponding confirmation button to the select a joint location (base, mid, end). If this is successful, the joint name will be visible above the clicked button.

<img src=assets/confirmCtrlJoint.png>

* **optional:**
Type a override name for which you wish the control to be named
> Note: The override name does not include the prefix.

<img src=assets/overrideCtrlName.png>

### **Additional Control Options:**
* To toggle the root control being rigged, click the "Create Root Control" checkbox.

<img src=assets/toggleRootCtrl.png>
<img src=assets/toggleRootDifference.png>

*Above: With Rig Control enabled on Left; Without Rig Control enabled on Right*


* To toggle the volume maintain attribute being added, click the "Create Volume Attribute" checkbox.
>Note: this attriubute will be housed on the "base" control.

<img src=assets/toggleVolumeCtrl.png>
<img src=assets/volumeMaintainDifference.png>

*Above: Volume Maintain off on Left; Volume Maintain enabled on Right*
>Note: Volume Maintain can still be turned off when the attribute is made. View the base controls attributes to edit.
* Change the prefix name of all controls.
<img src=assets/prefixName.png>

* Change the controls sizes by typing the desired control size.
<img src=assets/ctrlSize.png>

* Change the controls colors by clicking the color picker widget.

<img src=assets/colorPicker.png>

<img src=assets/getColorWidget.png>

* Select a color and confirm to change the control color.

<img src=assets/colorSelected.png>

### **Creating the chain controllers:**
* Once the settings are set, select the "" button to create the controls.
<img src=assets/createCtrlsButton.png>

### **Auto rig output:**

<img src=assets/chainOutput.png>

