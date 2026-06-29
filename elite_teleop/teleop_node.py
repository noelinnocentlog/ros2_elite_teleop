#!/usr/bin/env python3
"""
Xbox Elite controller  ->  cmd_vel  teleop node.

TAP the drive button (RB) to turn driving ON, tap again for OFF.
No more holding.

  Left stick  up/down    ->  forward / back
  Right stick left/right ->  turn
  RT (right trigger)     ->  boost  (go faster)
  LT (left trigger)      ->  precision (go slower)
  P1 paddle              ->  E-STOP (hard lock).  Press Menu to release.

Sends Twist OR TwistStamped (set 'publish_stamped' in the yaml).
Everything lives in config/elite_teleop.yaml.
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from geometry_msgs.msg import Twist, TwistStamped


def lerp(a, b, t):
    return a + (b - a) * t


def slew(cur, target, max_step):
    if target > cur:
        return min(cur + max_step, target)
    return max(cur - max_step, target)


class EliteTeleop(Node):
    def __init__(self):
        super().__init__('elite_teleop')

        self.declare_parameter('axis_linear', 1)
        self.declare_parameter('axis_angular', 3)
        self.declare_parameter('axis_boost', 5)
        self.declare_parameter('axis_slow', 2)
        self.declare_parameter('button_enable', 5)        # RB -> TAP to toggle
        self.declare_parameter('button_estop', 12)        # P1 -> hard e-stop
        self.declare_parameter('button_estop_clear', 7)   # Menu -> release e-stop

        self.declare_parameter('publish_stamped', False)
        self.declare_parameter('frame_id', 'base_link')

        self.declare_parameter('invert_linear', False)
        self.declare_parameter('invert_angular', False)

        self.declare_parameter('linear_normal', 0.4)
        self.declare_parameter('linear_turbo', 0.9)
        self.declare_parameter('linear_creep', 0.12)
        self.declare_parameter('angular_normal', 1.0)
        self.declare_parameter('angular_creep', 0.4)

        self.declare_parameter('deadzone', 0.12)
        self.declare_parameter('linear_accel', 1.5)
        self.declare_parameter('angular_accel', 3.0)
        self.declare_parameter('publish_rate', 50.0)
        self.declare_parameter('joy_timeout', 0.4)

        g = lambda n: self.get_parameter(n).value
        self.ax_lin   = g('axis_linear');   self.ax_ang  = g('axis_angular')
        self.ax_boost = g('axis_boost');    self.ax_slow = g('axis_slow')
        self.b_enable = g('button_enable'); self.b_estop = g('button_estop')
        self.b_clear  = g('button_estop_clear')
        self.use_stamped = g('publish_stamped'); self.frame_id = g('frame_id')
        self.inv_lin  = g('invert_linear'); self.inv_ang = g('invert_angular')
        self.lin_normal = g('linear_normal'); self.lin_turbo = g('linear_turbo')
        self.lin_creep  = g('linear_creep')
        self.ang_normal = g('angular_normal'); self.ang_creep = g('angular_creep')
        self.deadzone   = g('deadzone')
        self.lin_accel  = g('linear_accel');  self.ang_accel = g('angular_accel')
        self.rate       = g('publish_rate');  self.timeout   = g('joy_timeout')

        # state
        self.last_joy = None
        self.last_joy_time = self.get_clock().now()
        self.cur_lin = 0.0
        self.cur_ang = 0.0
        self.driving = False          # toggled by RB
        self.estop = False
        self.prev_enable = 0          # for tap (edge) detection

        msg_type = TwistStamped if self.use_stamped else Twist
        self.pub = self.create_publisher(msg_type, 'cmd_vel', 10)
        self.create_subscription(Joy, 'joy', self.on_joy, 10)
        self.dt = 1.0 / self.rate
        self.create_timer(self.dt, self.on_timer)

        kind = 'TwistStamped' if self.use_stamped else 'Twist'
        self.get_logger().info(
            f'elite_teleop ready ({kind}).  TAP RB to toggle driving.  P1 = e-stop.')

    def publish_cmd(self, lin, ang):
        if self.use_stamped:
            msg = TwistStamped()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = self.frame_id
            msg.twist.linear.x = lin
            msg.twist.angular.z = ang
        else:
            msg = Twist()
            msg.linear.x = lin
            msg.angular.z = ang
        self.pub.publish(msg)

    def on_joy(self, msg):
        self.last_joy = msg
        self.last_joy_time = self.get_clock().now()

    @staticmethod
    def trig(raw):
        return (1.0 - raw) / 2.0

    def axis(self, msg, idx):
        if idx < 0 or idx >= len(msg.axes):
            return 0.0
        v = msg.axes[idx]
        return 0.0 if abs(v) < self.deadzone else v

    def button(self, msg, idx):
        if idx < 0 or idx >= len(msg.buttons):
            return 0
        return msg.buttons[idx]

    def on_timer(self):
        # SAFETY WATCHDOG
        age = (self.get_clock().now() - self.last_joy_time).nanoseconds / 1e9
        if self.last_joy is None or age > self.timeout:
            self.cur_lin = 0.0
            self.cur_ang = 0.0
            self.publish_cmd(0.0, 0.0)
            return

        msg = self.last_joy

        # RB TAP -> toggle driving on/off (rising edge only)
        enable_btn = self.button(msg, self.b_enable)
        if enable_btn and not self.prev_enable:
            self.driving = not self.driving
            self.get_logger().info(
                'DRIVING ON' if self.driving else 'DRIVING OFF')
        self.prev_enable = enable_btn

        # E-STOP: hard lock until Menu releases it
        if self.button(msg, self.b_estop):
            if not self.estop:
                self.get_logger().warn('E-STOP! (press Menu to release)')
            self.estop = True
            self.driving = False
        if self.button(msg, self.b_clear) and self.estop:
            self.estop = False
            self.get_logger().info('E-stop released.')

        if self.estop:
            self.cur_lin = 0.0
            self.cur_ang = 0.0
            self.publish_cmd(0.0, 0.0)   # instant hard stop
            return

        target_lin = 0.0
        target_ang = 0.0

        if self.driving:
            stick_lin = self.axis(msg, self.ax_lin)
            stick_ang = self.axis(msg, self.ax_ang)
            if self.inv_lin:
                stick_lin = -stick_lin
            if self.inv_ang:
                stick_ang = -stick_ang

            boost = self.trig(msg.axes[self.ax_boost]) if self.ax_boost < len(msg.axes) else 0.0
            slow  = self.trig(msg.axes[self.ax_slow])  if self.ax_slow  < len(msg.axes) else 0.0

            max_lin = lerp(self.lin_normal, self.lin_turbo, boost)
            max_lin = lerp(max_lin, self.lin_creep, slow)
            max_ang = lerp(self.ang_normal, self.ang_creep, slow)

            target_lin = stick_lin * max_lin
            target_ang = stick_ang * max_ang

        self.cur_lin = slew(self.cur_lin, target_lin, self.lin_accel * self.dt)
        self.cur_ang = slew(self.cur_ang, target_ang, self.ang_accel * self.dt)
        self.publish_cmd(self.cur_lin, self.cur_ang)


def main():
    rclpy.init()
    node = EliteTeleop()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.publish_cmd(0.0, 0.0)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
