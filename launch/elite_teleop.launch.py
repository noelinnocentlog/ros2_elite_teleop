from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    config = os.path.join(
        get_package_share_directory('elite_teleop'),
        'config', 'elite_teleop.yaml')

    cmd_vel_topic = LaunchConfiguration('cmd_vel_topic', default='cmd_vel')

    return LaunchDescription([
        DeclareLaunchArgument(
            'cmd_vel_topic',
            default_value='cmd_vel',
            description='Topic name to publish velocity commands on',
        ),
        DeclareLaunchArgument(
            'device_id',
            default_value='0',
            description='Controller device index (see: ros2 run joy joy_enumerate_devices)',
        ),

        # reads the controller and publishes /joy
        Node(
            package='joy',
            executable='joy_node',
            name='joy_node',
            parameters=[{
                'device_id': LaunchConfiguration('device_id'),
                'deadzone': 0.0,
                'autorepeat_rate': 20.0,
            }],
        ),

        # turns /joy into cmd_vel
        Node(
            package='elite_teleop',
            executable='teleop_node',
            name='elite_teleop',
            parameters=[config],
            output='screen',
            remappings=[('cmd_vel', cmd_vel_topic)],
        ),
    ])
