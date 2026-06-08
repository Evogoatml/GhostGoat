import paramiko
from typing import Dict, List
import threading

class AgentNetwork:
    def __init__(self):
        self.agents = {
            # Local agents (same device)
            'local_agent_1': {
                'host': '127.0.0.1',
                'port': 8022,
                'username': 'chewlo',
                'type': 'local'
            },
            'local_agent_2': {
                'host': '127.0.0.1',
                'port': 8023,
                'username': 'chewlo',
                'type': 'local'
            },
            # Remote agents (other devices)
            # Add your actual IPs here
            'remote_agent_1': {
                'host': '192.168.1.XXX',  # Replace with actual IP
                'port': 8022,
                'username': 'chewlo',
                'type': 'remote'
            }
        }
        self.connections = {}
        self.key_file = '/data/data/com.termux/files/home/.ssh/id_ed25519'
    
    def connect_agent(self, agent_name):
        """Connect to a specific agent"""
        if agent_name not in self.agents:
            raise ValueError(f"Agent {agent_name} not found")
        
        config = self.agents[agent_name]
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            client.connect(
                hostname=config['host'],
                port=config['port'],
                username=config['username'],
                key_filename=self.key_file,
                timeout=10
            )
            self.connections[agent_name] = client
            print(f"✓ Connected to {agent_name}")
            return True
        except Exception as e:
            print(f"✗ Failed to connect to {agent_name}: {e}")
            return False
    
    def connect_all(self):
        """Connect to all agents"""
        for agent_name in self.agents:
            self.connect_agent(agent_name)
    
    def execute(self, agent_name, command):
        """Execute command on specific agent"""
        if agent_name not in self.connections:
            self.connect_agent(agent_name)
        
        client = self.connections[agent_name]
        stdin, stdout, stderr = client.exec_command(command)
        return {
            'stdout': stdout.read().decode(),
            'stderr': stderr.read().decode(),
            'exit_code': stdout.channel.recv_exit_status()
        }
    
    def broadcast(self, command):
        """Execute command on all agents"""
        results = {}
        threads = []
        
        def run_on_agent(agent_name):
            results[agent_name] = self.execute(agent_name, command)
        
        for agent_name in self.connections:
            t = threading.Thread(target=run_on_agent, args=(agent_name,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        return results
    
    def distribute_task(self, tasks: List[str]):
        """Distribute tasks across available agents"""
        results = {}
        agent_list = list(self.connections.keys())
        
        for i, task in enumerate(tasks):
            agent = agent_list[i % len(agent_list)]
            results[f"task_{i}_on_{agent}"] = self.execute(agent, task)
        
        return results
    
    def get_agent_status(self, agent_name):
        """Get system status from an agent"""
        return self.execute(agent_name, 
            "echo 'CPU:' && top -bn1 | grep 'Cpu' && "
            "echo 'MEM:' && free -h && "
            "echo 'DISK:' && df -h ~")
    
    def close_all(self):
        """Close all connections"""
        for name, client in self.connections.items():
            client.close()
            print(f"Disconnected from {name}")

# Usage Example
if __name__ == "__main__":
    network = AgentNetwork()
    network.connect_all()

    # Execute on specific agent
    result = network.execute('local_agent_1', 'python /path/to/task.py')
    print(result['stdout'])

    # Broadcast to all agents
    results = network.broadcast('whoami && hostname')
    for agent, result in results.items():
        print(f"{agent}: {result['stdout']}")

    # Distribute workload
    tasks = [
        'python task1.py',
        'python task2.py',
        'python task3.py',
        'python task4.py'
    ]
    results = network.distribute_task(tasks)

    # Check agent status
    status = network.get_agent_status('local_agent_1')
    print(status['stdout'])

    network.close_all()
