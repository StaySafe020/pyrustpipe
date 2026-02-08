use crate::types::ValidationResult;
use crate::validator::ValidationEngine;
use anyhow::{Context, Result};
use aws_config::meta::region::RegionProviderChain;
use aws_sdk_s3::Client;
use std::io::Write;
use tokio::io::AsyncReadExt;

impl ValidationEngine {
    /// Validate data from S3
    pub async fn validate_s3(
        &self,
        bucket: &str,
        key: &str,
        chunk_size: usize,
    ) -> Result<ValidationResult> {
        // Initialize AWS SDK
        let region_provider = RegionProviderChain::default_provider().or_else("us-east-1");
        let config = aws_config::defaults(aws_config::BehaviorVersion::latest())
            .region(region_provider)
            .load()
            .await;
        let client = Client::new(&config);

        // Download file from S3 to temporary location
        let temp_path = format!("/tmp/pyrustpipe_{}", key.replace('/', "_"));
        self.download_from_s3(&client, bucket, key, &temp_path)
            .await?;

        // Validate the downloaded file
        let result = self.validate_csv(&temp_path, chunk_size)?;

        // Clean up temporary file
        std::fs::remove_file(&temp_path).ok();

        Ok(result)
    }

    /// Download file from S3
    async fn download_from_s3(
        &self,
        client: &Client,
        bucket: &str,
        key: &str,
        dest_path: &str,
    ) -> Result<()> {
        let response = client
            .get_object()
            .bucket(bucket)
            .key(key)
            .send()
            .await
            .context("Failed to get object from S3")?;

        let mut file =
            std::fs::File::create(dest_path).context("Failed to create temporary file")?;

        let mut body = response.body.into_async_read();
        let mut buffer = vec![0; 8192];

        loop {
            let bytes_read = body.read(&mut buffer).await?;
            if bytes_read == 0 {
                break;
            }
            file.write_all(&buffer[..bytes_read])?;
        }

        Ok(())
    }

    /// Upload validation results to S3
    #[allow(dead_code)]
    pub async fn upload_results_to_s3(
        bucket: &str,
        key: &str,
        results: &ValidationResult,
    ) -> Result<()> {
        let region_provider = RegionProviderChain::default_provider().or_else("us-east-1");
        let config = aws_config::defaults(aws_config::BehaviorVersion::latest())
            .region(region_provider)
            .load()
            .await;
        let client = Client::new(&config);

        // Serialize results to JSON
        let json_data = serde_json::to_string_pretty(results)?;
        let body = aws_sdk_s3::primitives::ByteStream::from(json_data.into_bytes());

        client
            .put_object()
            .bucket(bucket)
            .key(key)
            .body(body)
            .content_type("application/json")
            .send()
            .await
            .context("Failed to upload results to S3")?;

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_s3_client_creation() {
        // Basic test to ensure S3 client can be created
        let region_provider = RegionProviderChain::default_provider().or_else("us-east-1");
        let config = aws_config::defaults(aws_config::BehaviorVersion::latest())
            .region(region_provider)
            .load()
            .await;
        let _client = Client::new(&config);
        // Test passes if we can create a client
    }
}
