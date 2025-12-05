output "security_group_id" {
  description = "ID of the created Security Group"
  value       = aws_security_group.managed.id
}

output "security_group_name" {
  description = "Name of the Security Group"
  value       = aws_security_group.managed.name
}
