use crate::error::{FilterError, FilterResult};

pub fn decode_base64(input: &str) -> FilterResult<Vec<u8>> {
    base64_decode(input).map_err(|e| FilterError::InternalError {
        message: format!("Base64 decode error: {}", e),
    })
}

pub fn encode_base64(input: &[u8]) -> String {
    base64_encode(input)
}

pub fn url_decode(input: &str) -> FilterResult<String> {
    percent_decode(input).map_err(|e| FilterError::InternalError {
        message: format!("URL decode error: {}", e),
    })
}

pub fn url_encode(input: &str) -> String {
    percent_encode(input)
}

fn base64_decode(input: &str) -> Result<Vec<u8>, String> {
    let input = input.trim_end_matches('=');
    let mut result = Vec::new();
    let mut buffer = 0u32;
    let mut bits = 0;

    for ch in input.bytes() {
        let value = if ch == b'+' {
            62
        } else if ch == b'/' {
            63
        } else if ch.is_ascii_uppercase() {
            ch - b'A'
        } else if ch.is_ascii_lowercase() {
            ch - b'a' + 26
        } else if ch.is_ascii_digit() {
            ch - b'0' + 52
        } else {
            return Err(format!("Invalid base64 character: {}", ch as char));
        };

        buffer = (buffer << 6) | value as u32;
        bits += 6;

        if bits >= 8 {
            bits -= 8;
            result.push((buffer >> bits) as u8);
            buffer &= (1 << bits) - 1;
        }
    }

    Ok(result)
}

fn base64_encode(input: &[u8]) -> String {
    const BASE64_CHARS: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

    let mut result = String::new();
    let mut buffer = 0u32;
    let mut bits = 0;

    for &byte in input {
        buffer = (buffer << 8) | byte as u32;
        bits += 8;

        while bits >= 6 {
            bits -= 6;
            let index = ((buffer >> bits) & 0x3F) as usize;
            result.push(BASE64_CHARS[index] as char);
            buffer &= (1 << bits) - 1;
        }
    }

    if bits > 0 {
        buffer <<= 6 - bits;
        let index = (buffer & 0x3F) as usize;
        result.push(BASE64_CHARS[index] as char);
    }

    while result.len() % 4 != 0 {
        result.push('=');
    }

    result
}

fn percent_decode(input: &str) -> Result<String, String> {
    let mut result = String::new();
    let mut chars = input.chars().peekable();

    while let Some(ch) = chars.next() {
        if ch == '%' {
            let hex1 = chars.next().ok_or("Incomplete percent encoding")?;
            let hex2 = chars.next().ok_or("Incomplete percent encoding")?;

            let byte = u8::from_str_radix(&format!("{}{}", hex1, hex2), 16)
                .map_err(|_| "Invalid hex in percent encoding")?;

            result.push(byte as char);
        } else if ch == '+' {
            result.push(' ');
        } else {
            result.push(ch);
        }
    }

    Ok(result)
}

fn percent_encode(input: &str) -> String {
    let mut result = String::new();

    for byte in input.bytes() {
        if byte.is_ascii_alphanumeric() || b"-_.~".contains(&byte) {
            result.push(byte as char);
        } else {
            result.push_str(&format!("%{:02X}", byte));
        }
    }

    result
}

pub fn escape_json_string(input: &str) -> String {
    let mut result = String::with_capacity(input.len());

    for ch in input.chars() {
        match ch {
            '"' => result.push_str("\\\""),
            '\\' => result.push_str("\\\\"),
            '\n' => result.push_str("\\n"),
            '\r' => result.push_str("\\r"),
            '\t' => result.push_str("\\t"),
            c if c.is_control() => {
                result.push_str(&format!("\\u{:04x}", c as u32));
            }
            c => result.push(c),
        }
    }

    result
}
