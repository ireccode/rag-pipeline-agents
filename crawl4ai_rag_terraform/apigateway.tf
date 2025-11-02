resource "aws_apigatewayv2_api" "lambda_api" {
  name          = "crawl4ai-mcp-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.crawl4ai.invoke_arn
  payload_format_version = "2.0"
  timeout_milliseconds   = 29000
}

resource "aws_apigatewayv2_route" "crawl4ai_route" {
  api_id    = aws_apigatewayv2_api.lambda_api.id
  route_key = "POST /crawl4ai"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.lambda_api.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "apigw_lambda_permission" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.crawl4ai.function_name
  principal     = "apigateway.amazonaws.com"

  # The /*/* is a wildcard for any stage and resource path
  source_arn = "${aws_apigatewayv2_api.lambda_api.execution_arn}/*/*"
}
