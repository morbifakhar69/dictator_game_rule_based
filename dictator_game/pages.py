from otree.api import *
from .models import Constants


# -----------------------------
#  General Introduction & Setup
# -----------------------------

class InformedConsent(Page):
    def is_displayed(self):
        return self.round_number == 1  # Show only once at the beginning


class Introduction(Page):
    def is_displayed(self):
        return self.round_number == 1  # Show only once at the beginning


class ComprehensionTest(Page):
    form_model = 'player'
    form_fields = ['q1', 'q2', 'q3', 'q4', 'q5', 'q6', 'q7', 'q8', 'q9', 'q10']

    def is_displayed(self):
        return not self.player.is_excluded and self.round_number == 1

    def error_message(self, values):
        correct_answers = {
            'q1': 'b',
            'q2': 'c',
            'q3': 'b',
            'q4': 'd',
            'q5': 'a',
            'q6': 'a',
            'q7': 'b',
            'q8': 'b',
            'q9': 'a',
            'q10': 'b',
        }

        incorrect = [
            q for q, correct in correct_answers.items()
            if values.get(q) != correct or not values.get(q)
        ]

        if incorrect:
            self.player.comprehension_attempts += 1

            if self.player.comprehension_attempts >= 3:
                self.player.is_excluded = True


            # elif self.player.comprehension_attempts == 2:
            #     return f"You answered the following question(s) incorrectly or left them blank: {', '.join(incorrect)}. This is your second failure. One more failure and you will be excluded."
            #
            # elif self.player.comprehension_attempts == 1:
            #     return f"You answered the following question(s) incorrectly or left them blank: {', '.join(incorrect)}. Please review the instructions and try again."

            self.player.incorrect_answers = ', '.join(incorrect)  # Log incorrect answers
            return None  # Allow participant to proceed without being excluded

class FailedTest(Page):
    def is_displayed(self):
        #return self.player.is_excluded
        return False


# -------------------------
#  Per-Part Instructions
# -------------------------

class Instructions(Page):
    def is_displayed(self):
        current_part = Constants.get_part(self.round_number)
        return not self.player.is_excluded and (self.round_number - 1) % Constants.rounds_per_part == 0

    def vars_for_template(self):
        current_part = Constants.get_part(self.round_number)
        return {
            'current_part': current_part,
            'incorrect_answers': self.player.incorrect_answers,

        }


# -------------------------
#  Agent Programming
# -------------------------

class AgentProgramming(Page):
    form_model = 'player'

    def is_displayed(self):
        current_part = Constants.get_part(self.round_number)
        return (
            (current_part == 2 or (current_part == 3 and self.player.delegate_decision_optional))
            and (self.round_number - 1) % Constants.rounds_per_part == 0
            #and not self.player.is_excluded
        )

    def get_form_fields(self):
        current_part = Constants.get_part(self.round_number)
        if current_part == 2:
            return [f"agent_allocation_mandatory_round_{i}" for i in range(1, 11)]
        elif current_part == 3:
            return [f"agent_allocation_optional_round_{i}" for i in range(1, 11)]

    
    def vars_for_template(self):
        current_part = Constants.get_part(self.round_number)
        return {
            'current_part': current_part
        }


    def before_next_page(self):
        current_part = Constants.get_part(self.round_number)
        if current_part in [2, 3]:
            part_rounds = self.player.in_rounds(
                (current_part - 1) * Constants.rounds_per_part + 1,
                current_part * Constants.rounds_per_part
            )
            for round_num in range(1, 11):
                allocation_field = (
                    f"agent_allocation_mandatory_round_{round_num}"
                    if current_part == 2
                    else f"agent_allocation_optional_round_{round_num}"
                )
                allocation_value = getattr(self.player, allocation_field)
                for p in part_rounds:
                    setattr(p, allocation_field, allocation_value)


# -------------------------
#  Decision Making
# -------------------------

class Decision(Page):
    form_model = 'player'
    form_fields = ['allocation']
    timeout_seconds = 20


    def is_displayed(self):
        current_part = Constants.get_part(self.round_number)
        return True

    def vars_for_template(self):
        current_part = Constants.get_part(self.round_number)
        display_round = (self.round_number - 1) % Constants.rounds_per_part + 1
        allocation = None
        if current_part == 2:
            allocation = self.player.get_agent_decision_mandatory(display_round)
        elif current_part == 3 and self.player.delegate_decision_optional:
            allocation = self.player.get_agent_decision_optional(display_round)
        #add logic to add allocation for part 1:

        return {
            'round_number': display_round,
            'current_part': current_part,
            'decision_mode': (
                "agent" if (current_part == 2 or (current_part == 3 and self.player.delegate_decision_optional)) else "manual"
            ),
            'player_allocation': allocation,
            'alert_message': self.participant.vars.get('alert_message', ""),
        }

    def before_next_page(self):
        import json
        import random

        #decisions = json.loads(self.player.random_decisions)
        #print(f"[DEBUG] Existing random_decisions: {decisions}")

        # Get current part and display round
        current_part = Constants.get_part(self.round_number)
        display_round = (self.round_number - 1) % Constants.rounds_per_part + 1

        if current_part == 1  :  # Part 1 logic or Part 3 with manual with manual decisions and timer
            if self.timeout_happened or self.player.allocation is None:
                # Assign random allocation if timer expires
                self.player.allocation = random.randint(0, 100)
                self.participant.vars['alert_message'] = (
                    f"You did not make a choice, so {self.player.allocation} was chosen for you. "
                )
                self.player.random_decisions = True
            else:
                # Clear the alert message if no timeout occurred
                self.participant.vars['alert_message'] = None
                self.player.random_decisions = False
            # Update decisions for the current round



        elif current_part == 2:  # Mandatory delegation
            self.player.allocation = self.player.get_agent_decision_mandatory(display_round)
            self.participant.vars['alert_message'] = ""
            self.player.random_decisions = True

        elif current_part == 3 and self.player.delegate_decision_optional:  # Optional delegation
            self.player.allocation = self.player.get_agent_decision_optional(display_round)
            self.participant.vars['alert_message'] = ""
            self.player.random_decisions = False



        print(f"round:{self.round_number}  self.player.allocation: {self.player.allocation}")


# -------------------------
#  Delegation Decision
# -------------------------

class DelegationDecision(Page):
    form_model = 'player'
    form_fields = ['delegate_decision_optional']

    def is_displayed(self):
        # Show only at the start of Part 3
        return Constants.get_part(self.round_number) == 3 and (self.round_number - 1) % Constants.rounds_per_part == 0

    def before_next_page(self):
        # Save the decision for all rounds in Part 3
        if Constants.get_part(self.round_number) == 3:
            part_rounds = self.player.in_rounds(
                (Constants.get_part(self.round_number) - 1) * Constants.rounds_per_part + 1,
                Constants.get_part(self.round_number) * Constants.rounds_per_part
            )
            for p in part_rounds:
                p.delegate_decision_optional = self.player.delegate_decision_optional



# -------------------------
#  Results
# -------------------------

class Results(Page):
    def is_displayed(self):
        return self.round_number % Constants.rounds_per_part == 0

    def vars_for_template(self):
        import json

        current_part = Constants.get_part(self.round_number)
        #decisions = json.loads(self.player.random_decisions)

        # Collect results for each round in the current part
        rounds_data = []
        for round_number in range(
            (current_part - 1) * Constants.rounds_per_part + 1,
            current_part * Constants.rounds_per_part + 1
        ):
            for player in self.subsession.get_players():
                round_result = player.in_round(round_number)
                rounds_data.append({
                    "round": round_number,
                    "decision": round_result.random_decisions,
                    "id_in_group": player.id_in_group,
                    "kept": 100 - (round_result.allocation or 0),
                    "allocated": round_result.allocation or 0,
                    "total": 100
                })

        return {
            'current_part': current_part,
            'rounds_data': rounds_data,

            #'decisions': decisions,
        }

        #this code is for random allocations
        # import json
        # current_part = Constants.get_part(self.round_number)
        # display_round = (self.round_number - 1) % Constants.rounds_per_part + 1
        # random_decisions = json.loads(self.player.random_decisions) if self.player.random_decisions else []
        # for decision in random_decisions:
        #     if decision.get("round") == self.round_number:
        #         current_round_status = decision.get("status", "Not Set")
        #         break
        # part_data = self.player.in_rounds(
        #     (current_part - 1) * Constants.rounds_per_part + 1,
        #     self.round_number
        # )
        #
        # rounds_data = [
        #     {
        #         'round_number': (player.round_number - 1) % Constants.rounds_per_part + 1,
        #         'allocated': player.allocation or 0,
        #         'kept': Constants.endowment - (player.allocation or 0),
        #     }
        #     for player in part_data
        # ]
        # print('Random Decisions: ',random_decisions)
        #
        # return {
        #     'current_part': current_part,
        #     'round_number': display_round,
        #     'rounds_data': rounds_data,
        #     'current_round_random': current_round_status,
        #     'all_random_decisions': random_decisions,  # All decisions for debugging
        #
        # }


# -------------------------
#  Debriefing
# -------------------------

class Debriefing(Page):
    def is_displayed(self):
        return not self.player.is_excluded and self.round_number == Constants.num_rounds


    def vars_for_template(self):
        import json

        results_by_part = {}

        # Loop through parts (1, 2, 3)
        for part in range(1, 4):
            part_data = []
            for round_number in range(
                (part - 1) * Constants.rounds_per_part + 1,
                part * Constants.rounds_per_part + 1
            ):
                round_result = self.player.in_round(round_number)
                part_data.append({
                    "round": round_number,
                    "kept": 100 - (round_result.allocation or 0),
                    "allocated": round_result.allocation or 0,
                    "decision" : round_result.random_decisions,
                })

            results_by_part[part] = part_data

        # Check if agent allocation was chosen in part 3
        agent_allocation_chosen = self.player.delegate_decision_optional

        return {
            'results_by_part': results_by_part,
            'agent_allocation_chosen': agent_allocation_chosen,
        }


# -------------------------
#  Page Sequence
# -------------------------

page_sequence = [
    InformedConsent,        # Only at the beginning
    Introduction,           # Only at the beginning
    ComprehensionTest,      # Only at the beginning
    FailedTest,             # If excluded after failing comprehension test
    Instructions,           # Once at the start of each part
    DelegationDecision,     # At the start of Part 3 to choose delegation
    AgentProgramming,       # Programming page for Part 2 or Part 3 (if delegation is chosen)
    Decision,               # Reusable for all parts (manual and agent-driven)
    Results,                # Reusable for all parts
    Debriefing,             # At the end or if excluded
]
