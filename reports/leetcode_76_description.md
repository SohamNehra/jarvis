# LeetCode 76: Minimum Window Substring

## Problem Overview

**Problem Statement:** Given two strings `s` and `t` of lengths `m` and `n` respectively, return the minimum window substring of `s` such that every character in `t` (including duplicates) is included in the window. If there is no such window, return an empty string `""`.

**Constraints:**
- `m == s.length`
- `n == t.length`
- `1 <= m, n <= 10^5`
- `s` and `t` consist of uppercase and lowercase English letters

**Example:**
```
Input: s = "ADOBECODEBANC", t = "ABC"
Output: "ADOBEC"
Explanation: The minimum window substring "ADOBEC" includes all characters in t.
```

## Approach: Sliding Window with Hash Map

The solution uses the **sliding window technique** combined with hash maps to efficiently find the minimum window substring.

### Algorithm Steps:

1. **Initialize Data Structures:**
   - Create a hash map `window` to track character frequencies in the current window
   - Create a hash map `t_count` to store the required character frequencies from string `t`
   - Track `formed` (number of unique characters in window with desired frequency)
   - Track `required` (number of unique characters needed from `t`)

2. **Expand the Window:**
   - Use a right pointer to expand the window by adding characters from `s`
   - Update the `window` hash map with the new character
   - If a character's count in the window matches its count in `t`, increment `formed`

3. **Contract the Window:**
   - When `formed == required`, we have a valid window
   - Use a left pointer to contract the window from the left
   - Track the minimum window found so far
   - Remove characters from the left until the window is no longer valid

4. **Return Result:**
   - Return the minimum window substring found, or empty string if none exists

### Pseudocode:

```
function minWindow(s, t):
    if len(t) > len(s):
        return ""
    
    t_count = frequency map of t
    window = empty frequency map
    formed = 0
    required = len(t_count)
    
    left = 0
    min_length = infinity
    min_left = 0
    
    for right in range(len(s)):
        character = s[right]
        window[character] += 1
        
        if character in t_count and window[character] == t_count[character]:
            formed += 1
        
        while left <= right and formed == required:
            character = s[left]
            
            if right - left + 1 < min_length:
                min_length = right - left + 1
                min_left = left
            
            window[character] -= 1
            if character in t_count and window[character] < t_count[character]:
                formed -= 1
            
            left += 1
    
    if min_length == infinity:
        return ""
    
    return s[min_left : min_left + min_length]
```

## Time Complexity

**O(m + n)** where:
- `m` is the length of string `s`
- `n` is the length of string `t`

**Explanation:**
- Building the `t_count` hash map takes **O(n)** time
- The right pointer traverses the entire string `s` once: **O(m)**
- The left pointer also traverses the entire string `s` once: **O(m)**
- Each character is visited at most twice (once by right pointer, once by left pointer)
- Hash map operations (insert, update, lookup) are **O(1)** on average

**Total: O(n + m + m) = O(m + n)**

## Space Complexity

**O(k)** where `k` is the number of unique characters in the alphabet

**Explanation:**
- The `window` hash map stores at most all unique characters from `s`: **O(k)**
- The `t_count` hash map stores at most all unique characters from `t`: **O(k)**
- Since we're dealing with English letters (uppercase and lowercase), `k ≤ 52`
- In practice, space complexity is **O(1)** for a fixed alphabet

## Key Insights

1. **Sliding Window Efficiency:** Rather than checking all possible substrings (O(m²) or worse), the sliding window technique ensures each character is processed a constant number of times.

2. **Two-Pointer Technique:** The left and right pointers move in one direction only, never backtracking, which guarantees linear time complexity.

3. **Frequency Matching:** Instead of checking if all characters are present, we track when the frequency requirements are met using the `formed` counter. This is more efficient than repeatedly validating the window.

4. **Contraction Phase:** The contraction phase is crucial—it removes unnecessary characters from the left, ensuring we find the minimum window. Without it, we'd only find a valid window, not necessarily the minimum one.

5. **Early Termination:** If `len(t) > len(s)`, we can immediately return an empty string without processing.

6. **Character Frequency Importance:** The problem requires matching character frequencies, not just presence. For example, if `t = "AAB"`, the window must contain at least 2 A's and 1 B.

## Implementation Considerations

- **Language-Specific:** The implementation may vary slightly depending on the programming language (e.g., using `defaultdict` in Python, `HashMap` in Java, `unordered_map` in C++)
- **Edge Cases:** Handle empty strings, strings where no valid window exists, and cases where `t` is longer than `s`
- **Optimization:** Using arrays instead of hash maps for character counting can be faster for fixed alphabets (52 characters for English letters)

## Related Problems

- LeetCode 3: Longest Substring Without Repeating Characters
- LeetCode 30: Substring with Concatenation of All Words
- LeetCode 438: Find All Anagrams in a String
- LeetCode 567: Permutation in String

## Conclusion

LeetCode 76 is a classic sliding window problem that demonstrates the power of the two-pointer technique. The key to solving it efficiently is recognizing that we don't need to check all possible substrings—instead, we can maintain a valid window and shrink it to find the minimum. This approach is fundamental to many string and array problems in competitive programming.
