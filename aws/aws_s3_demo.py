import boto3

s3 = boto3.client(
    "s3",
    region_name="ap-southeast-2"
)

response = s3.list_buckets()

for bucket in response.get("Buckets", []):
    print(bucket["Name"])