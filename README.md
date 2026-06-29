# elite_teleop — Xbox Elite 2 controller

A lightweight ROS 2 teleop package for the **Xbox Elite Series 2** controller.
Works over USB or Bluetooth ([xpadneo](https://github.com/atar-axis/xpadneo)).

Tested on ROS 2 Humble and Jazzy.

---

## Features

- **Tap-to-toggle driving** — tap RB once to start moving, tap again to stop (no hold required)
- **Boost / precision modes** — RT speeds up, LT slows down (both analog, mix freely)
- **E-stop** — P1 paddle instantly cuts all motion; Menu releases it
- **Acceleration slew limiting** — no jerky speed jumps
- **Safety watchdog** — publishes zero if the joy topic goes silent
- **Twist or TwistStamped** — one YAML flag switches message type

---

## Prerequisites

| Requirement | Notes |
|---|---|
| ROS 2 (Humble / Iron / Jazzy) | Older distros may work |
| `joy` package | `sudo apt install ros-$ROS_DISTRO-joy` |
| Xbox Elite 2 (USB or BT) | For Bluetooth: install [xpadneo](https://github.com/atar-axis/xpadneo) |

---

## Installation

```bash
cd ~/ros2_ws/src
git clone https://github.com/<your-username>/elite_teleop.git
cd ~/ros2_ws
colcon build --packages-select elite_teleop
source install/setup.bash
```

---

## Quick start

```bash
ros2 launch elite_teleop elite_teleop.launch.py
```

If your robot's cmd_vel topic is not `/cmd_vel`, pass a remapping:

```bash
ros2 launch elite_teleop elite_teleop.launch.py \
  cmd_vel_topic:=/my_robot/cmd_vel
```

Or edit the `remappings` line in `launch/elite_teleop.launch.py` directly.

---

## Controls

```
                        ┌─────────────────────────────┐
  LB ────────────────── │  ●  ●              LB    RB  │ ── RB  TAP = toggle driving
  LT (precision slow) ─ │                  LT      RT  │ ─ RT (boost fast)
                        │     ┌──────────────────┐     │
  Left stick ────────── │  ◉  │  ◉ view  menu ◉  │  ◉  │ ── Right stick (turn)
  (forward / back)      │     └──────────────────┘     │
                        │                              │
  P1 paddle (E-STOP) ── │  P1  P2          P3  P4      │
                        └─────────────────────────────┘
                                            Menu = clear E-stop
```

| Input | Action |
|---|---|
| **RB** (tap) | Toggle driving ON / OFF |
| **Left stick** up/down | Forward / reverse |
| **Right stick** left/right | Turn |
| **RT** (analog) | Boost — blends toward `linear_turbo` |
| **LT** (analog) | Precision — blends toward `linear_creep` / `angular_creep` |
| **P1 paddle** | **E-STOP** — hard zero, driving locked |
| **Menu** | Release E-stop |

---

## Configuration

All parameters live in `config/elite_teleop.yaml` — **no rebuild required** after editing.

### Message type (important!)

```yaml
publish_stamped: false   # false = Twist, true = TwistStamped
frame_id: base_link      # used only when publish_stamped: true
```

Set `publish_stamped: true` if your robot driver subscribes to `TwistStamped`
(e.g. Nav2 with the stamped interface).

### Full parameter reference

| Parameter | Default | Description |
|---|---|---|
| `axis_linear` | `1` | Stick axis index for forward/back |
| `axis_angular` | `3` | Stick axis index for turning |
| `axis_boost` | `5` | Trigger axis index for boost (RT) |
| `axis_slow` | `2` | Trigger axis index for precision (LT) |
| `button_enable` | `5` | Button index for drive toggle (RB) |
| `button_estop` | `12` | Button index for E-stop (P1 paddle) |
| `button_estop_clear` | `7` | Button index to clear E-stop (Menu) |
| `publish_stamped` | `false` | Publish `TwistStamped` instead of `Twist` |
| `frame_id` | `base_link` | Header frame id (stamped mode only) |
| `invert_linear` | `false` | Flip forward/back direction |
| `invert_angular` | `false` | Flip left/right turn direction |
| `linear_normal` | `0.4` | Normal linear speed (m/s) |
| `linear_turbo` | `0.9` | Boost linear speed (m/s) |
| `linear_creep` | `0.12` | Precision linear speed (m/s) |
| `angular_normal` | `1.0` | Normal angular speed (rad/s) |
| `angular_creep` | `0.4` | Precision angular speed (rad/s) |
| `deadzone` | `0.12` | Stick deadzone (applied before scaling) |
| `linear_accel` | `1.5` | Max linear acceleration (m/s²) |
| `angular_accel` | `3.0` | Max angular acceleration (rad/s²) |
| `publish_rate` | `50.0` | cmd_vel publish rate (Hz) |
| `joy_timeout` | `0.4` | Seconds of silence before zeroing output |

To find axis/button indices for your specific controller variant:

```bash
ros2 run joy joy_enumerate_devices
ros2 topic echo /joy
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Drives backwards | Set `invert_linear: true` in the yaml |
| Turns wrong way | Set `invert_angular: true` in the yaml |
| Controller not on `/dev/input/js0` | Change `device_id` in the launch file |
| Robot uses a different cmd_vel topic | Add a remapping in the launch file |
| Using ROS 2 Foxy | Replace `'device_id': 0` with `'dev': '/dev/input/js0'` in the launch file |
| No `/joy` messages | Run `ros2 run joy joy_node` separately and check `ros2 topic echo /joy` |
| Bluetooth connection drops | Use [xpadneo](https://github.com/atar-axis/xpadneo) for stable BT support |

---

## Package layout

```
elite_teleop/
├── config/
│   └── elite_teleop.yaml      # all tunable parameters
├── elite_teleop/
│   └── teleop_node.py         # the ROS 2 node
├── launch/
│   └── elite_teleop.launch.py # brings up joy_node + teleop_node
├── package.xml
└── setup.py
```

---

## Contributing

Issues and PRs welcome. If your controller variant uses different axis/button indices,
please open an issue with the output of `ros2 topic echo /joy` while pressing each input
and we can add a preset config.

---

## License

MIT — see [LICENSE](LICENSE).
