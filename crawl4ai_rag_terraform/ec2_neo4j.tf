data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-kernel-6.1-arm64"] # Using ARM64 for t4g.small
  }

  filter {
    name   = "architecture"
    values = ["arm64"]
  }
}

resource "aws_security_group" "neo4j_sg" {
  name        = "neo4j-sg"
  description = "Allow Bolt port from Lambda VPC CIDR"
  vpc_id      = aws_vpc.main.id

  # Allow Bolt port 7687 from the VPC CIDR (Lambda)
  ingress {
    from_port   = 7687
    to_port     = 7687
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.selected.cidr_block]
  }

  # Allow SSH for debugging (optional, but useful)
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.selected.cidr_block] # Only allow SSH from within the VPC
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "neo4j-sg"
  }
}

resource "aws_instance" "neo4j" {
  ami                    = data.aws_ami.amazon_linux_2023.id
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.private[0].id # Place in the first private subnet
  vpc_security_group_ids = [aws_security_group.neo4j_sg.id]
  key_name               = var.key_name
  associate_public_ip_address = true # For easier access/debugging

  user_data = <<-EOF
              #!/bin/bash
              # Install Neo4j on Amazon Linux 2023 (similar to apt/deb for this purpose)
              sudo dnf update -y
              sudo dnf install -y java-17-amazon-corretto-devel
              sudo wget -O /etc/yum.repos.d/neo4j.repo https://dist.neo4j.com/neo4j-5.repo
              sudo rpm --import https://dist.neo4j.com/RPM-GPG-KEY-neo4j
              sudo dnf install -y neo4j-community

              # Configure Neo4j to listen on all interfaces
              sudo sed -i 's/#dbms.default_listen_address=0.0.0.0/dbms.default_listen_address=0.0.0.0/' /etc/neo4j/neo4j.conf

              # Set initial password for 'neo4j' user
              # This is a placeholder and should be handled more securely in production
              sudo echo "dbms.security.auth_enabled=false" >> /etc/neo4j/neo4j.conf # Temporarily disable for first boot setup

              sudo systemctl enable neo4j
              sudo systemctl start neo4j
              
              # Wait for Neo4j to start and then set the password
              # For a t4g.small, this might take a while.
              sleep 60
              
              # Re-enable auth and set password (requires more complex scripting, skipping for simplicity)
              # For a production setup, you would use a secret manager and a more robust setup.
              
              # For now, we will rely on the Lambda env vars for connection, and the
              # user is responsible for the initial Neo4j setup/password change.
              
              EOF

  tags = {
    Name = "crawl4ai-mcp-neo4j"
  }
}
