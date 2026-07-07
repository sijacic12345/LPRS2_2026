#!/usr/bin/env python3

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    OpaqueFunction,
    IncludeLaunchDescription
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    LaunchConfiguration,
    ThisLaunchFileDir,
)
from launch_ros.actions import Node
from launch.conditions import IfCondition

import ackibot_utils.uname
from ackibot_utils.utils import show
from ackibot_utils.usb_mapper import USB_Mapper


def parse_bool(s):
    sl = s.lower()
    t = sl in ['true', '1', 'yes', 'y']
    f = sl in ['false', '0', 'no', 'n']
    if t:
        return True
    if f:
        return False
    raise TypeError(f'Cannot parse {s} to bool!')


def launch_setup(context, *args, **kwargs):
    en_teleop   = LaunchConfiguration('en_teleop',   default='true')
    en_auto     = LaunchConfiguration('en_auto',     default='true')
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')
    joypad      = LaunchConfiguration('joypad',      default='sony')

    um = USB_Mapper()
    show(um.table)
    arduino_port = um.get_exactly_1_dev_of_class('Arduino')
    show(arduino_port)

    params_fn = os.path.join(
        get_package_share_directory('ackibot_bringup'),
        'param',
        'ackibot.yaml'
    )

    twist_mux_cfg = os.path.join(
        get_package_share_directory('ackibot_bringup'),
        'config',
        'twist_mux_topics.yaml'
    )

    return [
        DeclareLaunchArgument('use_sim_time', default_value=use_sim_time,
            description='Use simulation clock if true'),
        DeclareLaunchArgument('en_teleop', default_value=en_teleop,
            description='Launch teleop'),
        DeclareLaunchArgument('en_auto', default_value=en_auto,
            description='Launch lane follower auto node'),
        DeclareLaunchArgument('joypad', default_value='sony'),

        # State publisher
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                ThisLaunchFileDir(),
                '/state_publisher.launch.py'
            ]),
            launch_arguments={'use_sim_time': use_sim_time}.items(),
        ),

        # Teleop (joystick)
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                os.path.join(
                    get_package_share_directory('ackibot_teleop'),
                    'launch',
                    'teleop.launch.py'
                )
            ]),
            launch_arguments={
                'machine': 'sbc',
                'joypad': joypad
            }.items(),
            condition=IfCondition(en_teleop),
        ),

        # Filter node — blokira Twist(0,0) od teleopa
        Node(
            package='ackibot_node',
            executable='cmd_vel_filter_node.py',
            name='cmd_vel_filter_node',
            output='screen',
            condition=IfCondition(en_teleop),
        ),

        # Twist mux — prioriteti: joystick(100) > auto(50) > navigation(10)
        Node(
            package='twist_mux',
            executable='twist_mux',
            name='twist_mux',
            output='screen',
            parameters=[twist_mux_cfg],
            remappings=[
                ('cmd_vel_out', '/cmd_vel'),
            ],
        ),

        # Lane follower — autonomna vožnja
        Node(
            package='ackibot_node',
            executable='lane_follower_node.py',
            name='lane_follower_node',
            output='screen',
            condition=IfCondition(en_auto),
        ),

        # fw_node — šalje komande na Arduino
        Node(
            package='ackibot_node',
            executable='fw_node',
            parameters=[params_fn],
            arguments=['-i', arduino_port],
            output='screen',
            remappings=[
                ('cmd_vel', '/cmd_vel'),
            ],
        ),
    ]


def generate_launch_description():
    ld = LaunchDescription([
        OpaqueFunction(function=launch_setup)
    ])
    return ld