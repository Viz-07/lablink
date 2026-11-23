# Fair allocation

Each request gets five factors. Clamp each raw factor to `[0, 1]`, multiply by its weight, sum, and round to four decimal places.

| Factor | Weight | Raw value |
| --- | ---: | --- |
| Deadline urgency | 0.35 | `1 - days / 30`, where days is the gap from the requested start's campus date to the deadline. Default 0.2 with no deadline. |
| Recent-use fairness | 0.25 | `1 - occupied_minutes / 600 - min(no_shows, 3) × 0.1`. Occupied minutes come from the previous seven days. |
| Project type | 0.20 | Capstone 1.0, research 0.9, competition 0.85, course 0.8, personal 0.4, no project 0.3. |
| Prior approval | 0.10 | 1 for a valid access grant or a previously approved booking, otherwise 0. |
| Waiting time | 0.10 | `hours_since_request / 72`. |

Eligibility checks cover past times, equipment status, training, deadline, opening hours, duration, weekly use limits, and overlap with the user's existing confirmed bookings. The allocator visits requests in descending score order, breaking ties by earlier creation time and then booking ID. It assigns the first unit in stable order whose timeline accommodates the whole interval. It also blocks overlaps with a placement made earlier in the same run.

Apply rechecks current state and creates slot locks atomically. A permitted reviewer can justify an override, and the service validates the proposed swap before it writes. Alternatives can use nearby times or similar equipment and are ranked by proximity, deadline margin, and lower recent utilisation. The service offers up to three, taking the winning assignments into account. Accepting an alternative rechecks that it remains feasible.

## Seeded spectrum analyser conflict

One Keysight unit is available for the contested window. The table shows the **weighted contributions**, with rounding for display.

| Request | Deadline | Fairness | Project | Approval | Waiting | Total | Result |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Aarav Shetty | 0.2917 | 0.2000 | 0.2000 | 0.1000 | 0.0278 | **0.8194** | Unit 1 |
| Sneha Pai | 0.1283 | 0.2500 | 0.1800 | 0.0000 | 0.0417 | **0.6000** | Capacity, three alternatives |
| Kabir Rao | 0.0700 | 0.1250 | 0.0800 | 0.0000 | 0.0028 | **0.2778** | Capacity, three alternatives |

Aarav's five-day gap gives a deadline contribution of `0.35 × (1 - 5/30)`. His 120 minutes of recent use give `0.25 × (1 - 120/600)`. His capstone, prior approval, and approximately 20 hours waiting produce the remaining contributions. Totals use the full-precision values.

The algorithm decides, Gemini explains. The same ranking and substitute slots are available with AI disabled.
