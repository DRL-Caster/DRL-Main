Store saved navigation assets here.

Recommended workflow:

1. Build a map with:
   `ros2 launch sensor_bringup slam_bringup.launch.py`
2. Save the occupancy grid:
   `ros2 run nav2_map_server map_saver_cli -f /home/kenbio/sensor_ws/src/sensor_bringup/maps/site_map`
3. Save the slam pose graph used by `slam_toolbox` localization:
   `ros2 service call /slam_toolbox/serialize_map slam_toolbox/srv/SerializePoseGraph "{filename: '/home/kenbio/sensor_ws/src/sensor_bringup/maps/site_map'}"`
4. Navigate with:
   `ros2 launch sensor_bringup nav_bringup.launch.py serialized_map:=/home/kenbio/sensor_ws/src/sensor_bringup/maps/site_map`
