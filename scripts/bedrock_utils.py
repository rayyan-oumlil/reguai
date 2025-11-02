"""
AWS Bedrock utility functions for model discovery and configuration.
"""

import boto3


def list_available_models(region_name: str = 'us-east-1', filter_by: str = 'claude'):
    """
    List available foundation models in AWS Bedrock.
    
    Args:
        region_name: AWS region (default: us-east-1)
        filter_by: Filter models by keyword (default: 'claude')
    
    Returns:
        List of available model IDs
    """
    try:
        bedrock = boto3.client('bedrock', region_name=region_name)
        response = bedrock.list_foundation_models()
        
        print(f"Available {filter_by.capitalize()} models in Bedrock ({region_name}):")
        available_models = []
        
        for model in response['modelSummaries']:
            if filter_by.lower() in model['modelId'].lower():
                print(f"  - {model['modelId']}")
                available_models.append(model['modelId'])
        
        return available_models
    except Exception as e:
        print(f"Error listing Bedrock models: {e}")
        return []


if __name__ == "__main__":
    # Example usage
    models = list_available_models()
