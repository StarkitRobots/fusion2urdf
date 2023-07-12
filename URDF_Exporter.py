#Author-Poleschuk Fedor
#Description-Generate URDF file from Fusion 360

import adsk, adsk.core, adsk.fusion, traceback
import os
import sys
from .utils import utils
from .utils import xacro
app = adsk.core.Application.get()
ui = app.userInterface
product = app.activeProduct
design = adsk.fusion.Design.cast(product)
title = 'Fusion2URDF'


packagepath = os.path.join(os.path.dirname(sys.argv[0]), 'Lib/site-packages/')
if packagepath not in sys.path:
    sys.path.append(packagepath)



from .core import Link, Joint, Write

"""
# length unit is 'cm' and inertial unit is 'kg/cm^2'
# If there is no 'body' in the root component, maybe the corrdinates are wrong.
"""

# joint effort: 100
# joint velocity: 100
# supports "Revolute", "Rigid" and "Slider" joint types

# I'm not sure how prismatic joint acts if there is no limit in fusion model

def run(context):
    def install_and_import(package):
            import importlib
            try:
                importlib.import_module(package)
            except ImportError:
                ui.messageBox('Install urdf2webots', "Install library")

                import pip
                pip.main(['install', package])
            finally:
                globals()[package] = importlib.import_module(package)


    app = adsk.core.Application.get()
    ui = app.userInterface
    install_and_import('urdf2webots')
# from urdf2webots.importer import convertUrdfContent


    try:
        import urdf2webots
    except:
        ui.messageBox('urdf2webots not installed', title)
    ui = None
    success_msg = 'Successfully create URDF file'
    msg = success_msg
        
    try:
        # --------------------
        # initialize
        app = adsk.core.Application.get()
        ui = app.userInterface
        product = app.activeProduct
        design = adsk.fusion.Design.cast(product)
        title = 'Fusion2URDF'
        if not design:
            ui.messageBox('No active Fusion design', title)
            return

        root = design.rootComponent  # root component 
        components = design.allComponents

        # set the names        
        robot_name = root.name.split()[0]
        package_name = robot_name + '_description'
        save_dir = utils.file_dialog(ui)
        if save_dir == False:
            ui.messageBox('Fusion2URDF was canceled', title)
            return 0
        
        save_dir = save_dir + '/' + package_name
        try: os.mkdir(save_dir)
        except: pass     

        package_dir = os.path.abspath(os.path.dirname(__file__)) + '/package/'
        
        # --------------------
        # set dictionaries
        
        # Generate joints_dict. All joints are related to root. 
        joints_dict, msg = Joint.make_joints_dict(root, msg)
        if msg != success_msg:
            ui.messageBox(msg, title)
            return 0   
        
        # Generate inertial_dict
        inertial_dict, msg = Link.make_inertial_dict(root, msg)
        if msg != success_msg:
            ui.messageBox(msg, title)
            return 0
        elif not 'base_link' in inertial_dict:
            msg = 'There is no base_link. Please set base_link and run again.'
            ui.messageBox(msg, title)
            return 0
        
        links_xyz_dict = {}
        
        # --------------------
        # Generate URDF
        Write.write_urdf(joints_dict, links_xyz_dict, inertial_dict, package_name, robot_name, save_dir)
        Write.write_materials_xacro(joints_dict, links_xyz_dict, inertial_dict, package_name, robot_name, save_dir)
        Write.write_transmissions_xacro(joints_dict, links_xyz_dict, inertial_dict, package_name, robot_name, save_dir)
        Write.write_gazebo_xacro(joints_dict, links_xyz_dict, inertial_dict, package_name, robot_name, save_dir)
        Write.write_display_launch(package_name, robot_name, save_dir)
        Write.write_gazebo_launch(package_name, robot_name, save_dir)
        Write.write_control_launch(package_name, robot_name, save_dir, joints_dict)
        Write.write_yaml(package_name, robot_name, save_dir, joints_dict)
        
        # copy over package files
        utils.copy_package(save_dir, package_dir)
        utils.update_cmakelists(save_dir, package_name)
        utils.update_package_xml(save_dir, package_name)

        # Generate STl files        
        utils.copy_occs(root)
        utils.export_stl(design, save_dir, components)  

        xacro.xacro(save_dir, robot_name)

        from urdf2webots.importer import convertUrdfFile

        try:
            import pathlib
            (version, cancelled) = ui.inputBox(
                'Version of webots {R2023b,R2023a,R2022b,R2022a,R2021b,R2021a,R2020b,R2020a}', 'Webots')
            # robot_description = pathlib.Path(
            #     save_dir+'/urdf/'+robot_name+'.urdf').read_text()
            # convertUrdfContent(input=robot_description)
            convertUrdfFile(input=save_dir+'/urdf/'+robot_name+'.urdf', output=save_dir+'/urdf/', targetVersion=version)
            

        except:
            ui.messageBox("proto", "Error")

        with open(os.path.join(save_dir, 'urdf', robot_name.title() + '.proto'), 'r') as file:
            data = file.read()
            data = data.replace("\\", "/")

        with open(os.path.join(save_dir, 'urdf', robot_name.title() + '.proto'), 'w') as file:
            file.write(data)
        
        ui.messageBox(msg, title)
        
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
