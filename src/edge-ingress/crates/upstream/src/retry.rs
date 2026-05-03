use edge_ingress_common::{
    constants::{MAX_RETRY_ATTEMPTS, RETRY_BACKOFF_MS},
    metrics::record_retry_attempt,
    EdgeError, Result,
};
use std::time::Duration;
use tokio::time::sleep;
use tracing::{debug, warn};

#[derive(Clone, Copy)]
pub struct RetryPolicy {
    max_attempts: u8,
    backoff_duration: Duration,
}

impl RetryPolicy {
    pub fn new(max_attempts: u8, backoff_ms: u64) -> Self {
        Self {
            max_attempts,
            backoff_duration: Duration::from_millis(backoff_ms),
        }
    }

    pub fn with_default() -> Self {
        Self::new(MAX_RETRY_ATTEMPTS, RETRY_BACKOFF_MS)
    }

    pub async fn execute<F, Fut, T>(&self, operation: F) -> Result<T>
    where
        F: Fn() -> Fut,
        Fut: std::future::Future<Output = Result<T>>,
    {
        let mut last_error = None;

        for attempt in 0..=self.max_attempts {
            if attempt > 0 {
                debug!(
                    attempt = attempt,
                    max_attempts = self.max_attempts,
                    backoff_ms = self.backoff_duration.as_millis(),
                    "retrying operation"
                );
                sleep(self.backoff_duration).await;
            }

            match operation().await {
                Ok(result) => {
                    if attempt > 0 {
                        record_retry_attempt("success");
                        debug!(
                            attempt = attempt,
                            "operation succeeded after retry"
                        );
                    }
                    return Ok(result);
                }
                Err(e) => {
                    if !e.is_retryable() {
                        warn!(
                            error = %e,
                            "operation failed with non-retryable error"
                        );
                        return Err(e);
                    }

                    debug!(
                        attempt = attempt,
                        error = %e,
                        "operation failed, will retry if attempts remain"
                    );
                    last_error = Some(e);
                }
            }
        }

        record_retry_attempt("exhausted");

        let error = last_error.unwrap_or_else(|| {
            EdgeError::Internal("Retry exhausted without error".to_string())
        });

        warn!(
            max_attempts = self.max_attempts,
            error = %error,
            "operation failed after all retry attempts"
        );

        Err(error)
    }

    pub fn max_attempts(&self) -> u8 {
        self.max_attempts
    }

    pub fn backoff_duration(&self) -> Duration {
        self.backoff_duration
    }
}

impl Default for RetryPolicy {
    fn default() -> Self {
        Self::with_default()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicU8, Ordering};
    use std::sync::Arc;

    #[test]
    fn test_new_retry_policy() {
        let policy = RetryPolicy::new(3, 100);
        assert_eq!(policy.max_attempts(), 3);
        assert_eq!(policy.backoff_duration(), Duration::from_millis(100));
    }

    #[test]
    fn test_with_default() {
        let policy = RetryPolicy::with_default();
        assert_eq!(policy.max_attempts(), MAX_RETRY_ATTEMPTS);
        assert_eq!(policy.backoff_duration(), Duration::from_millis(RETRY_BACKOFF_MS));
    }

    #[tokio::test]
    async fn test_execute_success_first_attempt() {
        let policy = RetryPolicy::new(3, 10);
        let result = policy.execute(|| async { Ok::<_, EdgeError>(42) }).await;
        assert!(result.is_ok());
        assert_eq!(result.unwrap(), 42);
    }

    #[tokio::test]
    async fn test_execute_success_after_retry() {
        let policy = RetryPolicy::new(3, 10);
        let counter = Arc::new(AtomicU8::new(0));
        let counter_clone = Arc::clone(&counter);

        let result = policy
            .execute(|| {
                let counter = Arc::clone(&counter_clone);
                async move {
                    let count = counter.fetch_add(1, Ordering::SeqCst);
                    if count < 2 {
                        Err(EdgeError::UpstreamConnectionFailed("test".to_string()))
                    } else {
                        Ok(42)
                    }
                }
            })
            .await;

        assert!(result.is_ok());
        assert_eq!(result.unwrap(), 42);
        assert_eq!(counter.load(Ordering::SeqCst), 3);
    }

    #[tokio::test]
    async fn test_execute_non_retryable_error() {
        let policy = RetryPolicy::new(3, 10);
        let counter = Arc::new(AtomicU8::new(0));
        let counter_clone = Arc::clone(&counter);

        let result = policy
            .execute(|| {
                let counter = Arc::clone(&counter_clone);
                async move {
                    counter.fetch_add(1, Ordering::SeqCst);
                    Err::<i32, _>(EdgeError::InvalidRequest("test".to_string()))
                }
            })
            .await;

        assert!(result.is_err());
        assert_eq!(counter.load(Ordering::SeqCst), 1);
    }

    #[tokio::test]
    async fn test_execute_exhausted_retries() {
        let policy = RetryPolicy::new(2, 10);
        let counter = Arc::new(AtomicU8::new(0));
        let counter_clone = Arc::clone(&counter);

        let result = policy
            .execute(|| {
                let counter = Arc::clone(&counter_clone);
                async move {
                    counter.fetch_add(1, Ordering::SeqCst);
                    Err::<i32, _>(EdgeError::UpstreamConnectionFailed("test".to_string()))
                }
            })
            .await;

        assert!(result.is_err());
        assert_eq!(counter.load(Ordering::SeqCst), 3);
    }
}
