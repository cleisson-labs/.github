/// Returns 42.
///
/// ```
/// assert_eq!(workflow_smoke::answer(), 42);
/// ```
pub fn answer() -> u8 {
    42
}

#[cfg(test)]
mod tests {
    use super::answer;

    #[test]
    fn instrumented_test_covers_the_library() {
        assert_eq!(answer(), 42);
    }
}
