# Wiring

Everything runs on 12 V from one power brick.

```text
 12 V 10 A brick ──(barrel pigtail)──┬──> PWM board  IN +/-  ──> OUT +/- ──> 775 motor
                                     │       (knob = speed, click = off)
                                     └──> 12 V pump (+/-), runs whenever the brick is plugged in
```

| Wire | Gauge |
|---|---|
| Brick → PWM board → motor | 18 AWG |
| Brick → pump | the pump's own leads |

- Wheels turning the wrong way? Swap the two motor wires.
- To stop the water without stopping the motor, close the airline valves.
- Keep the brick off the wet bench.
