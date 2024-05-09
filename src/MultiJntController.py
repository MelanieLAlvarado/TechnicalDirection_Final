#commandPort -name "localhost:7001" -sourceType "mel";
import maya.cmds as mc
from PySide2.QtCore import Signal, Qt
from PySide2.QtGui import QIntValidator, QDoubleValidator, QPalette, QColor, QPainter, QBrush, QRegExpValidator
from PySide2.QtWidgets import QCheckBox, QLineEdit, QWidget, QPushButton, QListWidget, QAbstractItemView, QLabel, QHBoxLayout, QVBoxLayout, QMessageBox, QColorDialog


def SetControllerColor(ctrlName, color:QColor):
    mc.setAttr(ctrlName + ".overrideEnabled",1)
    mc.setAttr(ctrlName + ".overrideRGBColors", 1)
    mc.setAttr(ctrlName + ".overrideColorRGB", color.redF(), color.greenF(), color.blueF())

class RigMultiJnt():
    def __init__(self):
        self.jntKey = ""
        self.rootJnt = ""
        self.baseJnt = ""
        self.midJnt = ""
        self.endJnt = ""
        self.shouldRigRoot = True
        self.shouldRigVolume = True
        
        self.chainJnts = set()
        self.drvJnts = set()

        self.controllerSize = 15
        self.controllerColor = QColor(0, 0, 0)
        self.ctrlPrefix = "ac_"
        self.overrideNames = ["base", "mid", "end"]

    def RigMultiJointChain(self, size = 15, color = QColor(0, 0, 0)):
        self.controllerColor = color
        self.controllerSize = size

        drvJntGrp = self.CreateDriverJnts()
        if self.shouldRigRoot == True:
            rootCtrl, rootCtrlGrp = self.CreateJntController(self.baseJnt, self.controllerSize + 2, self.controllerColor)
        
        baseCtrl, baseCtrlGrp = self.CreateJntController(self.baseJnt, self.controllerSize, self.controllerColor, True, self.overrideNames[0])
        midCtrl, midCtrlGrp = self.CreateJntController(self.midJnt, self.controllerSize, self.controllerColor, True, self.overrideNames[1])        
        endCtrl, endCtrlGrp = self.CreateJntController(self.endJnt, self.controllerSize, self.controllerColor, False, self.overrideNames[2])
        
        ikHandle, ikGrp = self.CreateDriverIK(baseCtrl, endCtrl)

        rigGrp = self.jntKey + "_rig_grp"
        mc.group(drvJntGrp, n = rigGrp)
        if self.shouldRigRoot ==True:
            mc.parent(midCtrlGrp, rootCtrl)
            mc.parent(baseCtrlGrp, rootCtrl)
            mc.parent(rootCtrlGrp, rigGrp)
        else:
            nonRootGrp = self.ctrlPrefix + self.jntKey + "_grp"
            mc.group(midCtrlGrp, n = nonRootGrp)
            mc.parent(baseCtrlGrp, nonRootGrp)
            mc.parent(nonRootGrp, rigGrp)
        mc.parent(endCtrlGrp, midCtrl)
        mc.parent(ikGrp, rigGrp)

        if self.shouldRigRoot == True:
            mc.parentConstraint(rootCtrl, drvJntGrp)
        """start of node section. might move into separate functions"""
        #ikHandle_spine.roll = ac_hips.rotateX;
        #.O[1] = ac_hips.rotateX + ac_spine.rotateX + ac_chest.rotateX;
        mc.expression(s = ikHandle + ".roll = " + baseCtrl + ".rotateX; " + ikHandle + ".twist = " + baseCtrl + ".rotateX + " + midCtrl + ".rotateX + " + endCtrl + ".rotateX;")

        #REAL NODE WORK STARTS!
        if self.shouldRigVolume == True:
            ikHandleSpine = mc.ls(ikHandle) #getting the actual ikHandle instead of a string name
            ikCurve = mc.listRelatives(ikGrp, c = True)[1] #getting curve

            curves = mc.listRelatives(ikCurve, s=True) #getting shapes
            curveShape = curves[0]
            curveShapeOrig = curves[1]

            currentCurveInfo = "CurveInfo_" + self.jntKey + "current_length"
            currentCurveInfo = mc.createNode("curveInfo", n = currentCurveInfo)
            print(currentCurveInfo)
            mc.connectAttr(curveShape + ".worldSpace", currentCurveInfo + ".inputCurve")

            origCurveInfo = "CurveInfo_" + self.jntKey+"original_length"
            print(origCurveInfo)
            origCurveInfo = mc.createNode("curveInfo", n = origCurveInfo)
            mc.connectAttr(curveShapeOrig+".worldSpace", origCurveInfo+".inputCurve")

            multDivStretchX = "multiplyDivide_"+self.jntKey+"_stretch_x"
            multDivStretchX = mc.createNode("multiplyDivide", n=multDivStretchX)
            mc.setAttr(multDivStretchX+".operation", 2) #Division
            mc.connectAttr(currentCurveInfo + ".arcLength", multDivStretchX + ".input1X")
            mc.connectAttr(origCurveInfo + ".arcLength", multDivStretchX + ".input2X")

            mc.connectAttr(multDivStretchX + ".outputX", self.drvJnts[0] + ".scaleX")

            #connecting driver joints' scales
            for i in range(0, len(self.drvJnts)):
                drvJnt = self.drvJnts[i]
                nextIndex = i + 1
                if nextIndex >= len(self.drvJnts):
                    break
                
                nextDrvJnt = self.drvJnts[nextIndex]
                if mc.objExists(nextDrvJnt):
                    mc.connectAttr(drvJnt + ".scaleX", nextDrvJnt + ".scaleX")

            #creating nodes for volume control
            multDivInvertScale = "multiplyDivide_"+self.jntKey+"_invert_scale"
            multDivInvertScale = mc.createNode("multiplyDivide", n=multDivInvertScale)
            mc.setAttr(multDivInvertScale+".operation", 3) #Power (0.5))
            mc.setAttr(multDivInvertScale+".input2X", 0.5)
            mc.connectAttr(multDivStretchX + ".outputX", multDivInvertScale + ".input1X")

            multDivScaleYZ = "multiplyDivide_"+self.jntKey+"scale_y_z"
            multDivScaleYZ = mc.createNode("multiplyDivide", n=multDivScaleYZ)
            mc.setAttr(multDivScaleYZ+".operation", 2) #Divide (1/n)
            mc.setAttr(multDivScaleYZ+".input1X", 1)
            mc.connectAttr(multDivInvertScale + ".outputX", multDivScaleYZ + ".input2X")
            print(f"adding volume ctrl attr {self.GetVolumeMaintainAttr()} to {endCtrl}")
            mc.addAttr(endCtrl, ln = self.GetVolumeMaintainAttr(),min = 0, max = 1, k=True)

            blendColors = "multiplyDivide_"+self.jntKey+"_volume_maintain"
            blendColors = mc.createNode("blendColors", n = blendColors)
            mc.connectAttr(multDivScaleYZ + ".outputX", blendColors + ".color1R")
            mc.connectAttr(endCtrl + "."+self.GetVolumeMaintainAttr(), blendColors+".blender")
            mc.setAttr(blendColors+".color2R", 1)

            self.midJnt
            index = 0
            midJntIndex = 0
            for jnt in self.chainJnts:
                if jnt == self.midJnt:
                    midJntIndex = index
                    break
                index += 1
            if mc.objExists(self.chainJnts[midJntIndex - 1]) and self.chainJnts[midJntIndex] != self.baseJnt:
                beforeMidJnt = self.chainJnts[midJntIndex - 1]
                mc.connectAttr(blendColors + ".outputR", beforeMidJnt + ".scaleY")
                mc.connectAttr(blendColors + ".outputR", beforeMidJnt + ".scaleZ")

                mc.connectAttr(beforeMidJnt + ".scaleY", self.midJnt+".scaleY", f=True)
                mc.connectAttr(beforeMidJnt + ".scaleZ", self.midJnt+".scaleZ", f=True)

            elif mc.objExists(self.chainJnts[midJntIndex + 1]) and self.chainJnts[midJntIndex] != self.endJnt:
                afterMidJnt = self.chainJnts[midJntIndex + 1]
                mc.connectAttr(blendColors + ".outputR", self.midJnt+".scaleY")
                mc.connectAttr(blendColors + ".outputR", self.midJnt+".scaleZ")

                mc.connectAttr(self.midJnt + ".scaleY", afterMidJnt+".scaleY", f=True)
                mc.connectAttr(self.midJnt + ".scaleZ", afterMidJnt+".scaleY", f=True)
            

    def CreateJntController(self, jnt, size = float(10), color = QColor(0, 0, 0), orientConstraint = True, overrideName = str("")):
        if overrideName == "":
            ctrlName = self.ctrlPrefix + jnt
        else:
            ctrlName = self.ctrlPrefix + overrideName
        ctrlGrpName = ctrlName + "_grp"
        mc.circle(n=ctrlName, nr=(1, 0, 0), r = size)
        mc.group(ctrlName, n =ctrlGrpName)
        mc.matchTransform(ctrlGrpName, jnt)
        if orientConstraint == True:
            mc.orientConstraint(ctrlName, jnt)
        else: 
            mc.parentConstraint(ctrlName, jnt)
        SetControllerColor(ctrlName, color)
        return ctrlName, ctrlGrpName

    def CreateDriverJnts(self):
        jnts = list(self.chainJnts)
        dupJnts = mc.duplicate(jnts[0], n = "drv_" + jnts[0], rc = True)
        for dup in dupJnts:
            dup = "drv_" + dup
        drvJnts = []
        for dup in dupJnts:
            if mc.objExists(dup) and mc.objectType(dup) == "joint":
                drvJnts.append(dup)
                drvJnts = self.AddChildOfJoint(dup, drvJnts)
                break
        
        if len(drvJnts) == 0:
            return False, "No Joint Selected!"

        dupJnts.reverse()
        for dup in dupJnts:
            if dup not in drvJnts:
                mc.delete(dup)
        index = 0
        initialJntNames = list(self.chainJnts)
        renamedDrvJnt = []
        for drv in drvJnts:
            drv = mc.rename(drv, "drv_" + initialJntNames[index], ignoreShape = True)
            renamedDrvJnt.append(drv)
            index += 1

        drvJntGrp = self.jntKey + "_drv_grp"
        mc.group(renamedDrvJnt[0], n=drvJntGrp)
        self.drvJnts = set(renamedDrvJnt)
        self.drvJnts = sorted(set(renamedDrvJnt), key=renamedDrvJnt.index)
        return drvJntGrp


    def CreateDriverIK(self, baseCtrl, endCtrl):
        startDrvJnt = mc.ls(self.drvJnts, type='joint')[0]
        endDrvJnt = mc.listRelatives(self.drvJnts, ad=True, type='joint')[0]
        
        ikHandleName = "ikHandle_" + self.jntKey
        ikCurve = mc.ikHandle(n=ikHandleName, sj = startDrvJnt, ee = endDrvJnt, sol = "ikSplineSolver")[2]
        
        upperVerts = mc.ls(f"{ikCurve}.cv[2:3]")
        upperCluster = self.jntKey + "_upper_cluster"
        upperCluster = mc.cluster(upperVerts, n = upperCluster)
        mc.parent(upperCluster[1], endCtrl)

        lowerVerts = mc.ls(f"{ikCurve}.cv[0:1]")
        lowerCluster = self.jntKey + "_lower_cluster"
        lowerCluster = mc.cluster(lowerVerts, n = lowerCluster)
        mc.parent(lowerCluster[1], baseCtrl)
        
        ikGrp = "IK_" + self.jntKey + "_grp"
        mc.group(ikHandleName, ikCurve, n = ikGrp)

        startChainJnt = mc.ls(self.chainJnts, type='joint')[0]
        endChainJnt = mc.ls(self.chainJnts, type='joint')
        endChainJnt.reverse()
        endChainJnt = endChainJnt[0]

        tempDrvList = list(self.drvJnts)
        tempDrvList.remove(startDrvJnt)
        tempDrvList.remove(endDrvJnt)
        print(tempDrvList)

        tempChainList = list(self.chainJnts)
        tempChainList.remove(startChainJnt)
        tempChainList.remove(endChainJnt)
        print(tempChainList)
        index = 0
        for chain in tempChainList:
            mc.parentConstraint(tempDrvList[index], chain)
            index += 1
        print(self.drvJnts)
        print(self.chainJnts)
        print(ikCurve)
        return ikHandleName, ikGrp

    def AddChildOfJoint(self, jnt, jnts:list):
        nextJnts = mc.listRelatives(jnt, c=True)
        if not nextJnts:
            return jnts
        for j in nextJnts:
            if mc.objectType(j) == "joint" and str(self.jntKey) in str(j):
                jnts.append(j)
                self.AddChildOfJoint(j, jnts)
                return jnts

    def AddLoopedJoints(self):
        selection = mc.ls(sl=True)
        jnts = []
        if not selection:
            return jnts
        self.chainJnts.clear()
        print(selection)
        for sel in selection:
            if mc.objExists(sel) and mc.objectType(sel) == "joint":
                print(f"find joint {sel}")
                jnts.append(sel)
                jnts = self.AddChildOfJoint(sel, jnts)
                return jnts

    def AddSelectedJnts(self):
        jnts = self.AddLoopedJoints()
        if not jnts or len(jnts) == 0:
            return False, "No Valid Joints detected!"
        elif len(jnts) < 3:
            return False, "Not enough Joints Found!\nPlease have at least 3 joints, All including the keyword.\n(The first joint does not require the keyword)"
        else:
            self.chainJnts = set(jnts)
            self.chainJnts = sorted(set(jnts), key=jnts.index)
            print(f"self.chainJnts : {self.chainJnts}")
            return True, ""

    def AssignBaseJnt(self):
        sel = mc.ls(sl=True)
        if not sel:
            return False, "Nothing Selected!"
        tempJnt = sel[0]
        if mc.objExists(tempJnt) and mc.objectType(tempJnt) == "joint":
            if tempJnt == self.midJnt or tempJnt == self.endJnt:
                return False, "Please select a Unique Joint for the Base!"
            
            tempChain = list(self.chainJnts)
            tempChain.reverse()
            baseList = []
            for i in range(0, len(tempChain)):
                if tempChain[i] == tempJnt:
                    if self.midJnt not in baseList and self.midJnt != "":
                        return False, "Base Joint must be Above the Middle Joint!"
                    elif self.endJnt not in baseList and self.endJnt != "":
                        return False, "Base Joint must be Above the End Joint!"
                elif tempChain[i] == self.midJnt:
                    baseList.append(tempChain[i])
                    continue
                elif tempChain[i] == self.endJnt:
                    baseList.append(tempChain[i])
                    continue
            self.baseJnt = tempJnt
            return True, ""
        else:
            return False, "First Selection is not a joint!"

    def AssignMidJnt(self):
        sel = mc.ls(sl=True)
        if not sel:
            return False, "Nothing Selected!"
        tempJnt = sel[0]
        if mc.objExists(tempJnt) and mc.objectType(tempJnt) == "joint":
            if tempJnt == self.baseJnt or tempJnt == self.endJnt:
                return False, "Please select a Unique Joint for the Middle!"
            
            tempChain = list(self.chainJnts)
            tempChain.reverse()
            baseList = []
            for i in range(0, len(tempChain)):
                if tempChain[i] == tempJnt:
                    if self.endJnt not in baseList and self.endJnt != "":
                        return False, "Middle Joint must be Above the End Joint!"
                elif tempChain[i] == self.endJnt:
                    baseList.append(tempChain[i])
                    continue

            if self.baseJnt in mc.listRelatives(tempJnt, ad = True):
                return False, "Middle Joint must be underneath the Base Joint!"
            self.midJnt = tempJnt
            return True, ""
        else:
            return False, "First Selection is not a joint!"

    def AssignEndJnt(self):
        sel = mc.ls(sl=True)
        if not sel:
            return False, "Nothing Selected!"
        tempJnt = sel[0]
        if mc.objExists(tempJnt) and mc.objectType(tempJnt) == "joint":
            if tempJnt == self.baseJnt or tempJnt == self.midJnt:
                return False, "Please select a Unique Joint for the End!"
            if mc.listRelatives(tempJnt, ad = True):
                if self.midJnt in mc.listRelatives(tempJnt, ad = True):
                    return False, "End Joint must be underneath the Middle Joint!"
            self.endJnt = tempJnt
            return True, ""
        else:
            return False, "First Selection is not a joint!"
        
    def ClearJntsList(self):
        self.rootJnt = ""
        self.baseJnt = ""
        self.midJnt = ""
        self.endJnt = ""

    def GetVolumeMaintainAttr(self):
        return "Volume_Maintain"

class ColorPicker(QWidget):
    colorChanged = Signal(QColor)
    def __init__(self, width = 80, height = 20):
        super().__init__()
        self.setFixedSize(width, height)
        self.color = QColor(128, 128, 128)

    def mousePressEvent(self, event):
        color = QColorDialog().getColor(self.color)
        if color.isValid():
            self.color = color
            self.colorChanged.emit(self.color)
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setBrush(QBrush(self.color))
        painter.drawRect(0, 0, self.width(), self.height())

class MultiJntWidget(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Create Multiple Joint Chain")
        self.setGeometry(0, 0, 600, 300)
        self.rigMultiJnt = RigMultiJnt()

        self.masterLayout = QHBoxLayout()
        self.setLayout(self.masterLayout)

        self.jointSelectionLayout = QVBoxLayout()
        self.CreateJntSelection()
        self.masterLayout.addLayout(self.jointSelectionLayout)

        jointCustomizationLayout = QVBoxLayout()
        hintLabel = QLabel("|Select each of the corresponding joints of the chain and confirm,\n|then choose the name of the controls")
        jointCustomizationLayout.addWidget(hintLabel)

        ctrlOptionLayout = QHBoxLayout()

        ctrlLocationSelLayout = QVBoxLayout()

        self.selectedBaseLabel = QLineEdit()
        self.selectedBaseLabel.setEnabled(False)
        ctrlLocationSelLayout.addWidget(self.selectedBaseLabel)
        confirmBaseBtn = QPushButton("Confirm as Base Joint")
        confirmBaseBtn.clicked.connect(self.BaseJntBtnClicked)
        ctrlLocationSelLayout.addWidget(confirmBaseBtn)

        self.selectedMidLabel = QLineEdit()
        self.selectedMidLabel.setEnabled(False)
        ctrlLocationSelLayout.addWidget(self.selectedMidLabel)
        confirmMidBtn = QPushButton("Confirm as Middle Joint")
        confirmMidBtn.clicked.connect(self.MidJntBtnClicked)
        ctrlLocationSelLayout.addWidget(confirmMidBtn)

        self.selectedEndLabel = QLineEdit()
        self.selectedEndLabel.setEnabled(False)
        ctrlLocationSelLayout.addWidget(self.selectedEndLabel)
        confirmEndBtn = QPushButton("Confirm as End Joint")
        confirmEndBtn.clicked.connect(self.EndJntBtnClicked)
        ctrlLocationSelLayout.addWidget(confirmEndBtn)

        ctrlOptionLayout.addLayout(ctrlLocationSelLayout)

        self.overrideNameLayout = QVBoxLayout()
        self.CreateOverrideNameSettings()
        ctrlOptionLayout.addLayout(self.overrideNameLayout)

        jointCustomizationLayout.addLayout(ctrlOptionLayout)

        self.additionalOptionsLayout = QHBoxLayout()
        self.ctrlSize = QLineEdit()
        self.CreateCntrlSettingSection()
        jointCustomizationLayout.addLayout(self.additionalOptionsLayout)

        rigButton = QPushButton("Rig Multi-Chain")
        rigButton.clicked.connect(self.RigMultiChainBtnClicked)
        jointCustomizationLayout.addWidget(rigButton)
        self.masterLayout.addLayout(jointCustomizationLayout)

    def ChainKeyNameSet(self, valStr:str):
        key = valStr
        self.rigMultiJnt.jntKey = key

    def BaseJntBtnClicked(self):
        success, msg = self.rigMultiJnt.AssignBaseJnt()
        if not success:
            QMessageBox().warning(self, "Warning", str(msg))
            return
        self.selectedBaseLabel.setText(f"{self.rigMultiJnt.baseJnt}")
    
    def MidJntBtnClicked(self):
        success, msg = self.rigMultiJnt.AssignMidJnt()
        if not success:
            QMessageBox().warning(self, "Warning", str(msg))
            return
        self.selectedMidLabel.setText(f"{self.rigMultiJnt.midJnt}")

    def EndJntBtnClicked(self):
        success, msg = self.rigMultiJnt.AssignEndJnt()
        if not success:
            QMessageBox().warning(self, "Warning", str(msg))
            return
        self.selectedEndLabel.setText(f"{self.rigMultiJnt.endJnt}")

    def RigMultiChainBtnClicked(self):
        size = float(self.ctrlSize.text())
        color = self.ctrlColorPicker.color
        success, msg = self.VerifySettings(size)
        if not success:
            QMessageBox().warning(self, "Warning", str(msg))
            return
        self.rigMultiJnt.RigMultiJointChain(size = size, color = color)

    def VerifySettings(self, size):
        if not self.rigMultiJnt.chainJnts or len(self.rigMultiJnt.chainJnts) == 0:
            return False, "There Are No Found Joints!"
        if size <= 0:
            return False, "Size Must be More Than Zero!"
        if self.rigMultiJnt.baseJnt == "":
            return False, "Base Joint Must be Assigned to Rig!"
        elif self.rigMultiJnt.midJnt == "":
            return False,  "Middle Joint Must be Assigned to Rig!"
        elif self.rigMultiJnt.endJnt == "":
            return False, "End Joint Must be Assigned to Rig!"
        if self.rigMultiJnt.ctrlPrefix == "":
            return False, "Must Include a Prefix for the Controls!"
        return True, ""

    def EnableRootToggled(self):
        self.rigMultiJnt.shouldRigRoot = not self.rigMultiJnt.shouldRigRoot

    def EnableVolumeToggled(self):
        self.rigMultiJnt.shouldRigVolume = not self.rigMultiJnt.shouldRigVolume

    def CtrlPrefixSet(self, valStr:str):
        prefixName = str(valStr)
        self.rigMultiJnt.ctrlPrefix = prefixName

    def BaseNameSet(self, valStr:str):
        baseName = str(valStr)
        self.rigMultiJnt.overrideNames[0] = baseName

    def MidNameSet(self, valStr:str):
        midName = str(valStr)
        self.rigMultiJnt.overrideNames[1] = midName

    def EndNameSet(self, valStr:str):
        endName = str(valStr)
        self.rigMultiJnt.overrideNames[2] = endName

    def CtrlSizeValueSet(self, valStr:str):
        size = float(valStr)
        self.rigMultiJnt.controllerSize = size

    def CtrlColorPickerColorChanged(self, newColor:QColor):
        self.rigMultiJnt.controllerColor = QColor(newColor)

    def AddJointsBtnClicked(self):
        if self.rigMultiJnt.jntKey == "":
            msg = "Please Type a Keyword for the Joints to be Selected"
            QMessageBox().warning(self, "Warning", str(msg))
            return
        success, msg = self.rigMultiJnt.AddSelectedJnts()
        if not success:
            self.jntList.clear()
            self.rigMultiJnt.ClearJntsList()
            self.SetAllJointConfirmations()
            QMessageBox().warning(self, "Warning", str(msg))
            return
        else:
            self.jntList.clear()
            self.rigMultiJnt.ClearJntsList()
            self.SetAllJointConfirmations()
            self.jntList.addItems(self.rigMultiJnt.chainJnts)

    def OnJntListSelectionChanged(self):
        mc.select(cl=True)
        for item in self.jntList.selectedItems():
            mc.select(item.text(), add=True)

    def SetAllJointConfirmations(self):
        self.selectedBaseLabel.setText(f"{self.rigMultiJnt.baseJnt}")
        self.selectedMidLabel.setText(f"{self.rigMultiJnt.midJnt}")
        self.selectedEndLabel.setText(f"{self.rigMultiJnt.endJnt}")

    def CreateJntSelection(self):
        findJointHint = QLabel("Select the highest hierachical joint in the chain \nthen type a keyword that matches the related joints")
        self.jointSelectionLayout.addWidget(findJointHint)

        self.jntList = QListWidget()
        self.jntList.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.jntList.itemSelectionChanged.connect(self.OnJntListSelectionChanged)
        self.jointSelectionLayout.addWidget(self.jntList)


        keyLayout = QHBoxLayout()
        keyNameLabel = QLabel("Joint Keyname:")
        keyLayout.addWidget(keyNameLabel)

        self.chainKeyName = QLineEdit()
        self.chainKeyName.setValidator(QRegExpValidator("\w+"))
        self.chainKeyName.setText("(spine, neck, etc.)")
        self.chainKeyName.textChanged.connect(self.ChainKeyNameSet)
        keyLayout.addWidget(self.chainKeyName)
        self.jointSelectionLayout.addLayout(keyLayout)

        setSelectedJntsBtn = QPushButton("Auto Find Joints")
        setSelectedJntsBtn.clicked.connect(self.AddJointsBtnClicked)
        self.jointSelectionLayout.addWidget(setSelectedJntsBtn)
        self.jntList.addItems(self.rigMultiJnt.chainJnts)

    def CreateCntrlSettingSection(self):
        self.prefixLabel = QLabel("Control Prefix:")
        self.additionalOptionsLayout.addWidget(self.prefixLabel)

        self.prefixEdit = QLineEdit()
        self.prefixEdit.setText("ac_")
        self.prefixEdit.textChanged.connect(self.CtrlPrefixSet)
        self.additionalOptionsLayout.addWidget(self.prefixEdit)

        sizeLabel = QLabel("Control Size")
        self.additionalOptionsLayout.addWidget(sizeLabel)

        self.ctrlSize.setValidator(QDoubleValidator())
        self.ctrlSize.setText("15")
        self.ctrlSize.textChanged.connect(self.CtrlSizeValueSet)
        self.additionalOptionsLayout.addWidget(self.ctrlSize)

        self.ctrlColorPicker = ColorPicker()
        self.ctrlColorPicker.colorChanged.connect(self.CtrlColorPickerColorChanged)
        self.additionalOptionsLayout.addWidget(self.ctrlColorPicker)
        
    def CreateOverrideNameSettings(self):
        self.baseNameOverrideLabel = QLabel("Base Control Name:")
        self.overrideNameLayout.addWidget(self.baseNameOverrideLabel)
        self.baseNameOverride = QLineEdit()
        self.baseNameOverride.setText("base")
        self.baseNameOverride.textChanged.connect(self.BaseNameSet)
        self.overrideNameLayout.addWidget(self.baseNameOverride)

        self.midNameOverrideLabel = QLabel("Middle Control Name:")
        self.overrideNameLayout.addWidget(self.midNameOverrideLabel)
        self.midNameOverride = QLineEdit()
        self.midNameOverride.setText("mid")
        self.midNameOverride.textChanged.connect(self.MidNameSet)
        self.overrideNameLayout.addWidget(self.midNameOverride)

        self.endNameOverrideLabel = QLabel("End Control Name:")
        self.overrideNameLayout.addWidget(self.endNameOverrideLabel)
        self.endNameOverride = QLineEdit()
        self.endNameOverride.setText("end")
        self.endNameOverride.textChanged.connect(self.EndNameSet)
        self.overrideNameLayout.addWidget(self.endNameOverride)

        rootCheckLayout = QHBoxLayout()
        rigRootLabel = QLabel("Create Root Control")
        rootCheckLayout.addWidget(rigRootLabel)

        enableRootCtrl = QCheckBox()
        enableRootCtrl.setChecked(self.rigMultiJnt.shouldRigRoot)
        rootCheckLayout.addWidget(enableRootCtrl)
        enableRootCtrl.toggled.connect(self.EnableRootToggled)
        self.overrideNameLayout.addLayout(rootCheckLayout)

        volumeCheckLayout = QHBoxLayout()
        volumeLabel = QLabel("Create Volume Attribute")
        volumeCheckLayout.addWidget(volumeLabel)

        enableVolumeCtrl = QCheckBox()
        enableVolumeCtrl.setChecked(self.rigMultiJnt.shouldRigRoot)
        volumeCheckLayout.addWidget(enableVolumeCtrl)
        enableVolumeCtrl.toggled.connect(self.EnableVolumeToggled)
        self.overrideNameLayout.addLayout(volumeCheckLayout)


multiJntWidget = MultiJntWidget()
multiJntWidget.show()
