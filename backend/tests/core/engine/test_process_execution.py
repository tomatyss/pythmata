# """Tests for process execution functionality."""

# import pytest
# from uuid import uuid4
# from pythmata.api.schemas import ProcessVariableValue

# from tests.conftest import BaseEngineTest, assert_token_state, assert_process_variables


# @pytest.mark.asyncio
# class TestProcessExecution(BaseEngineTest):
#     async def test_basic_sequence_flow(self):
#         """Test execution of a simple sequence flow: Start -> Task -> End."""
#         instance_id = str(uuid4())
#         process_graph = self.create_sequence_flow()

#         # Create initial token
#         token = await self.executor.create_initial_token(instance_id, "Start_1")
#         assert token.node_id == "Start_1"

#         # Execute process
#         await self.executor.execute_process(instance_id, process_graph)

#         # Verify final state
#         await assert_token_state(self.state_manager, instance_id, 0)

#     async def test_exclusive_gateway_flow(self):
#         """Test execution with exclusive gateway."""
#         instance_id = str(uuid4())
#         process_graph = self.create_exclusive_flow({
#             "Task_1": "true",  # This path will be taken
#             "Task_2": "false"  # This path won't be taken
#         })

#         # Create initial token
#         token = await self.executor.create_initial_token(instance_id, "Start_1")
#         assert token.node_id == "Start_1"

#         # Execute process
#         await self.executor.execute_process(instance_id, process_graph)

#         # Verify final state
#         await assert_token_state(self.state_manager, instance_id, 0)

#     async def test_parallel_gateway_flow(self):
#         """Test execution with parallel gateway."""
#         instance_id = str(uuid4())
#         process_graph = self.create_parallel_flow(["Task_1", "Task_2"])

#         # Create initial token
#         token = await self.executor.create_initial_token(instance_id, "Start_1")
#         assert token.node_id == "Start_1"

#         # Execute process
#         await self.executor.execute_process(instance_id, process_graph)

#         # Verify final state
#         await assert_token_state(self.state_manager, instance_id, 0)

#     async def test_inclusive_gateway_flow(self):
#         """Test execution with inclusive gateway."""
#         instance_id = str(uuid4())

#         # Set up test variables
#         amount_var = ProcessVariableValue(type="float", value=150.0)
#         await self.state_manager.set_variable(
#             instance_id=instance_id,
#             name="amount",
#             variable=amount_var
#         )

#         # Create process graph with inclusive gateway
#         process_graph = self.create_exclusive_flow({
#             "Task_1": "variables.get('amount', 0) >= 100",  # High priority
#             "Task_2": "variables.get('amount', 0) >= 50",   # Medium priority
#             "Task_3": "variables.get('amount', 0) >= 0"     # Low priority
#         })

#         # Create initial token
#         token = await self.executor.create_initial_token(instance_id, "Start_1")
#         assert token.node_id == "Start_1"

#         # Execute process
#         await self.executor.execute_process(instance_id, process_graph)

#         # Verify final state
#         await assert_token_state(self.state_manager, instance_id, 0)

#         # Verify variables
#         await assert_process_variables(self.state_manager, instance_id, {
#             "amount": amount_var
#         })
