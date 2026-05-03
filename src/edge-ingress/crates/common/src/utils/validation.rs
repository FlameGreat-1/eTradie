use crate::constants::{MAX_HEADER_SIZE, MAX_REQUEST_SIZE};
use crate::error::{EdgeError, Result};
use crate::types::Region;
use std::net::SocketAddr;
use std::time::Duration;

pub type ValidationResult<T> = Result<T>;

pub fn validate_header_size(size: usize) -> Result<()> {
    if size > MAX_HEADER_SIZE {
        return Err(EdgeError::HeaderTooLarge {
            size,
            max: MAX_HEADER_SIZE,
        });
    }
    Ok(())
}

pub fn validate_request_size(size: usize) -> Result<()> {
    if size > MAX_REQUEST_SIZE {
        return Err(EdgeError::RequestTooLarge {
            size,
            max: MAX_REQUEST_SIZE,
        });
    }
    Ok(())
}

pub fn validate_socket_addr(addr: &str) -> Result<SocketAddr> {
    addr.parse::<SocketAddr>()
        .map_err(|e| EdgeError::Configuration(format!("Invalid socket address '{}': {}", addr, e)))
}

pub fn validate_region(region_str: &str) -> Result<Region> {
    Region::from_str(region_str)
        .ok_or_else(|| EdgeError::Configuration(format!("Invalid region: {}", region_str)))
}

pub fn validate_timeout(duration: Duration, min: Duration, max: Duration) -> Result<Duration> {
    if duration < min {
        return Err(EdgeError::Configuration(format!(
            "Timeout {:?} is below minimum {:?}",
            duration, min
        )));
    }
    if duration > max {
        return Err(EdgeError::Configuration(format!(
            "Timeout {:?} exceeds maximum {:?}",
            duration, max
        )));
    }
    Ok(duration)
}

pub fn validate_port(port: u16) -> Result<u16> {
    if port == 0 {
        return Err(EdgeError::Configuration("Port cannot be 0".to_string()));
    }
    Ok(port)
}

pub fn validate_connection_limit(limit: usize, min: usize, max: usize) -> Result<usize> {
    if limit < min {
        return Err(EdgeError::Configuration(format!(
            "Connection limit {} is below minimum {}",
            limit, min
        )));
    }
    if limit > max {
        return Err(EdgeError::Configuration(format!(
            "Connection limit {} exceeds maximum {}",
            limit, max
        )));
    }
    Ok(limit)
}

pub fn validate_hostname(hostname: &str) -> Result<String> {
    if hostname.is_empty() {
        return Err(EdgeError::Configuration("Hostname cannot be empty".to_string()));
    }
    
    if hostname.len() > 253 {
        return Err(EdgeError::Configuration(format!(
            "Hostname too long: {} characters (max 253)",
            hostname.len()
        )));
    }
    
    let labels: Vec<&str> = hostname.split('.').collect();
    for label in labels {
        if label.is_empty() || label.len() > 63 {
            return Err(EdgeError::Configuration(format!(
                "Invalid hostname label: '{}'",
                label
            )));
        }
        
        if !label.chars().all(|c| c.is_ascii_alphanumeric() || c == '-') {
            return Err(EdgeError::Configuration(format!(
                "Hostname label contains invalid characters: '{}'",
                label
            )));
        }
        
        if label.starts_with('-') || label.ends_with('-') {
            return Err(EdgeError::Configuration(format!(
                "Hostname label cannot start or end with hyphen: '{}'",
                label
            )));
        }
    }
    
    Ok(hostname.to_string())
}

pub fn validate_retry_attempts(attempts: u8, max: u8) -> Result<u8> {
    if attempts > max {
        return Err(EdgeError::Configuration(format!(
            "Retry attempts {} exceeds maximum {}",
            attempts, max
        )));
    }
    Ok(attempts)
}

pub fn validate_health_check_threshold(threshold: u32, min: u32, max: u32) -> Result<u32> {
    if threshold < min {
        return Err(EdgeError::Configuration(format!(
            "Health check threshold {} is below minimum {}",
            threshold, min
        )));
    }
    if threshold > max {
        return Err(EdgeError::Configuration(format!(
            "Health check threshold {} exceeds maximum {}",
            threshold, max
        )));
    }
    Ok(threshold)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_validate_header_size_valid() {
        assert!(validate_header_size(1024).is_ok());
        assert!(validate_header_size(MAX_HEADER_SIZE).is_ok());
    }

    #[test]
    fn test_validate_header_size_invalid() {
        assert!(validate_header_size(MAX_HEADER_SIZE + 1).is_err());
    }

    #[test]
    fn test_validate_request_size_valid() {
        assert!(validate_request_size(1024).is_ok());
        assert!(validate_request_size(MAX_REQUEST_SIZE).is_ok());
    }

    #[test]
    fn test_validate_request_size_invalid() {
        assert!(validate_request_size(MAX_REQUEST_SIZE + 1).is_err());
    }

    #[test]
    fn test_validate_socket_addr_valid() {
        assert!(validate_socket_addr("127.0.0.1:8080").is_ok());
        assert!(validate_socket_addr("[::1]:8080").is_ok());
    }

    #[test]
    fn test_validate_socket_addr_invalid() {
        assert!(validate_socket_addr("invalid").is_err());
        assert!(validate_socket_addr("127.0.0.1").is_err());
    }

    #[test]
    fn test_validate_region_valid() {
        assert!(validate_region("us-east-1").is_ok());
        assert!(validate_region("eu-west-1").is_ok());
    }

    #[test]
    fn test_validate_region_invalid() {
        assert!(validate_region("invalid-region").is_err());
    }

    #[test]
    fn test_validate_timeout_valid() {
        let min = Duration::from_secs(1);
        let max = Duration::from_secs(60);
        assert!(validate_timeout(Duration::from_secs(5), min, max).is_ok());
    }

    #[test]
    fn test_validate_timeout_below_min() {
        let min = Duration::from_secs(5);
        let max = Duration::from_secs(60);
        assert!(validate_timeout(Duration::from_secs(1), min, max).is_err());
    }

    #[test]
    fn test_validate_timeout_above_max() {
        let min = Duration::from_secs(1);
        let max = Duration::from_secs(60);
        assert!(validate_timeout(Duration::from_secs(120), min, max).is_err());
    }

    #[test]
    fn test_validate_port_valid() {
        assert!(validate_port(8080).is_ok());
        assert!(validate_port(443).is_ok());
    }

    #[test]
    fn test_validate_port_invalid() {
        assert!(validate_port(0).is_err());
    }

    #[test]
    fn test_validate_hostname_valid() {
        assert!(validate_hostname("example.com").is_ok());
        assert!(validate_hostname("sub.example.com").is_ok());
        assert!(validate_hostname("my-service.namespace.svc.cluster.local").is_ok());
    }

    #[test]
    fn test_validate_hostname_invalid() {
        assert!(validate_hostname("").is_err());
        assert!(validate_hostname("-invalid.com").is_err());
        assert!(validate_hostname("invalid-.com").is_err());
        assert!(validate_hostname("invalid..com").is_err());
    }

    #[test]
    fn test_validate_retry_attempts_valid() {
        assert!(validate_retry_attempts(1, 3).is_ok());
    }

    #[test]
    fn test_validate_retry_attempts_invalid() {
        assert!(validate_retry_attempts(5, 3).is_err());
    }

    #[test]
    fn test_validate_health_check_threshold_valid() {
        assert!(validate_health_check_threshold(3, 1, 10).is_ok());
    }

    #[test]
    fn test_validate_health_check_threshold_below_min() {
        assert!(validate_health_check_threshold(0, 1, 10).is_err());
    }

    #[test]
    fn test_validate_health_check_threshold_above_max() {
        assert!(validate_health_check_threshold(15, 1, 10).is_err());
    }
}
