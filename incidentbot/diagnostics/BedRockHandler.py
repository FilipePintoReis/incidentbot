import boto3
import uuid

class BedRockHandler:
    @staticmethod
    def invoke_bedrock_agent(agent_id, agent_alias_id, input_text, region="eu-west-2", session_id=None, enable_trace=False, end_session=False):
        """
        Invokes an Amazon Bedrock Agent.

        Args:
            agent_id (str): The unique identifier of the agent to use.
            agent_alias_id (str): The alias of the agent to use (e.g., 'DRAFT', 'Prod').
            input_text (str): The user prompt for the agent to process.
            session_id (str, optional): To continue the same conversation, use the same sessionId.
                                        If None, a new session ID will be generated.
            enable_trace (bool, optional): Set to True to activate trace enablement for debugging.
            end_session (bool, optional): Set to True to end the conversation session.

        Returns:
            dict: The agent's response.
        """
        client = boto3.client("bedrock-agent-runtime", region_name=region)

        if session_id is None:
            session_id = str(uuid.uuid4()) 

        response = client.invoke_agent(
            agentId=agent_id,
            agentAliasId=agent_alias_id,
            sessionId=session_id,
            inputText=input_text,
            enableTrace=enable_trace,
            endSession=end_session
        )

        # Process the streamed response
        # The 'completion' field contains an EventStream object for streaming responses
        # You'll need to iterate through it to get the full response.
        # For a non-streaming response, you might get a direct result, but it's often streamed.

        full_response_text = ""
        for event in response.get('completion'):
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    full_response_text += chunk['bytes'].decode('utf-8')
            #elif 'trace' in event and enable_trace:
                ## Handle trace events for debugging the agent's thought process
                #print(f"Trace Event: {event['trace']}")
            #elif 'attribution' in event:
                ## Handle attribution if your agent uses a Knowledge Base
                #print(f"Attribution: {event['attribution']}")

        return full_response_text

    @staticmethod
    def list_bedrock_agents(region_name="eu-west-2"):
        """
        Lists all Amazon Bedrock agents in a given region.

        Args:
            region_name (str): The AWS region to list agents from (e.g., "eu-west-2").

        Returns:
            list: A list of dictionaries, where each dictionary contains
                information about an agent.
        """
        try:
            # Create a client for the bedrock-agent service
            client = boto3.client("bedrock-agent", region_name=region_name)

            # Use the list_agents API to retrieve agent summaries
            response = client.list_agents()

            agents = response.get('agentSummaries', [])

            if not agents:
                print(f"No Bedrock agents found in region: {region_name}")
                return []

            print(f"Found {len(agents)} Bedrock agent(s) in region: {region_name}")
            for agent in agents:
                print(f"  Agent ID: {agent.get('agentId')}")
                print(f"  Agent Name: {agent.get('agentName')}")
                print(f"  Agent Status: {agent.get('agentStatus')}")
                print(f"  Description: {agent.get('description', 'N/A')}")
                print(f"  Latest Agent Version: {agent.get('latestAgentVersion', 'N/A')}")
                print(f"  Last Updated: {agent.get('updatedAt')}")
                print("-" * 30)

            return agents

        except Exception as e:
            print(f"An error occurred: {e}")
            return []


print(BedRockHandler.invoke_bedrock_agent(
        agent_id="MH00AZX5TB",
        agent_alias_id="GIITVBBSUU",
        input_text="Hello, I'm Deep Purple. How are you today?",
        enable_trace=True, 
        end_session=False
))