"""Order sequencing managing FIFO order arrival and RUSH priority jumps (BR-03)."""

from typing import List

from src.models import Order


class OrderSequencer:
    """Applies FIFO sequencing and constrained RUSH priority jumps."""

    MAX_RUSH_JUMPS: int = 3
    MAX_DELAY_JUMPS: int = 2

    @classmethod
    def sequence_orders(cls, orders: List[Order]) -> List[Order]:
        """
        BR-03:
        1. Default order sequence is FIFO by order time.
        2. RUSH applies when channel priority flag is set or order value > ₹1,500.
        3. A RUSH order may jump ahead of up to 3 orders.
        4. An order cannot be delayed by more than 2 jumps.
        5. Track jumps explicitly.
        """
        # Baseline FIFO sort by order time
        queue = sorted(orders, key=lambda o: o.order_time)

        # Apply RUSH jumps
        for i in range(len(queue)):
            current = queue[i]
            if not current.is_rush:
                continue

            # Attempt to jump ahead of preceding orders
            j = i
            while j > 0 and current.rush_jumps_made < cls.MAX_RUSH_JUMPS:
                preceding = queue[j - 1]

                # Cannot jump ahead of another RUSH order
                if preceding.is_rush:
                    break

                # Cannot delay an order that has already been jumped MAX_DELAY_JUMPS times
                if preceding.delayed_jumps_count >= cls.MAX_DELAY_JUMPS:
                    break

                # Perform the jump
                queue[j - 1], queue[j] = queue[j], queue[j - 1]
                current.rush_jumps_made += 1
                preceding.delayed_jumps_count += 1
                j -= 1

        return queue
