# Copyright 2021 Tier IV, Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

import launch
from launch.actions import DeclareLaunchArgument
from launch.actions import GroupAction
from launch.actions import SetLaunchConfiguration
from launch.conditions import IfCondition
from launch.conditions import UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import ComposableNodeContainer
from launch_ros.actions import PushRosNamespace
from launch_ros.descriptions import ComposableNode
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    lanelet2_map_loader = ComposableNode(
        package='map_loader',
        plugin='Lanelet2MapLoaderNode',
        name='lanelet2_map_loader',
        remappings=[('output/lanelet2_map', 'vector_map')],
        parameters=[
            {
                'center_line_resolution': 5.0,
                'lanelet2_map_path': LaunchConfiguration('lanelet2_map_path'),
            }
        ],
        extra_arguments=[{
            'use_intra_process_comms': LaunchConfiguration('use_intra_process')
        }],
    )

    lanelet2_map_visualization = ComposableNode(
        package='map_loader',
        plugin='Lanelet2MapVisualizationNode',
        name='lanelet2_map_visualization',
        remappings=[('input/lanelet2_map', 'vector_map'),
                    ('output/lanelet2_map_marker', 'vector_map_marker')],
        extra_arguments=[{
            'use_intra_process_comms': LaunchConfiguration('use_intra_process')
        }],
    )

    pointcloud_map_loader = ComposableNode(
        package='map_loader',
        plugin='PointCloudMapLoaderNode',
        name='pointcloud_map_loader',
        remappings=[('output/pointcloud_map', 'pointcloud_map')],
        parameters=[
            {
                'pcd_paths_or_directory': ['[', LaunchConfiguration('pointcloud_map_path'), ']']
            }
        ],
        extra_arguments=[{
            'use_intra_process_comms': LaunchConfiguration('use_intra_process')
        }],
    )

    map_tf_generator = ComposableNode(
        package='map_tf_generator',
        plugin='MapTFGeneratorNode',
        name='map_tf_generator',
        parameters=[
            {
                'map_frame': 'map',
                'viewer_frame': 'viewer',
            }
        ],
        extra_arguments=[{
            'use_intra_process_comms': LaunchConfiguration('use_intra_process')
        }],
    )

    elevation_map_loader = ComposableNode(
        package='map_loader',
        plugin='ElevationMapLoaderNode',
        name='elevation_map_loader',
        remappings=[('output/elevation_map', 'elevation_map'),
                    ('input/pointcloud_map', 'pointcloud_map'),
                    ('input/vector_map', 'vector_map')],
        parameters=[
            {
                'param_file_path': LaunchConfiguration('elevation_map_param_file_path'),
                'use_lane_filter': False,
                'use_inpaint': True,
                'inpaint_radius': 1.0,
                'elevation_map_file_path': LaunchConfiguration('elevation_map_file_path'),
                'use_elevation_map_cloud_publisher': False,
            }
        ],
        extra_arguments=[{
            'use_intra_process_comms': LaunchConfiguration('use_intra_process')
        }],
    )

    container = ComposableNodeContainer(
        name='map_container',
        namespace='',
        package='rclcpp_components',
        executable=LaunchConfiguration('container_executable'),
        composable_node_descriptions=[
            lanelet2_map_loader,
            lanelet2_map_visualization,
            pointcloud_map_loader,
            map_tf_generator,
            elevation_map_loader,
        ],
        output='screen',
    )

    def add_launch_arg(name: str, default_value=None, description=None):
        return DeclareLaunchArgument(name, default_value=default_value, description=description)

    return launch.LaunchDescription([
        add_launch_arg('map_path', '', 'path to map directory'),
        add_launch_arg('lanelet2_map_path', [
                       LaunchConfiguration('map_path'), '/lanelet2_map.osm'],
                       'path to lanelet2 map file'),
        add_launch_arg('pointcloud_map_path', [
                       LaunchConfiguration('map_path'), '/pointcloud_map.pcd'],
                       'path to pointcloud map file'),
        add_launch_arg('use_intra_process', 'false', 'use ROS2 component container communication'),
        add_launch_arg('use_multithread', 'false', 'use multithread'),
        add_launch_arg('elevation_map_param_file_path',
                       os.path.join(FindPackageShare('map_launch').find('map_launch'),
                                    'config', 'elevation_map_parameters.yaml')),
        add_launch_arg('elevation_map_file_path', [
                       LaunchConfiguration('map_path'), '/elevation_map']),
        SetLaunchConfiguration(
            'container_executable',
            'component_container',
            condition=UnlessCondition(LaunchConfiguration('use_multithread'))
        ),
        SetLaunchConfiguration(
            'container_executable',
            'component_container_mt',
            condition=IfCondition(LaunchConfiguration('use_multithread'))
        ),
        GroupAction([
            PushRosNamespace('map'),
            container,
        ])
    ])
