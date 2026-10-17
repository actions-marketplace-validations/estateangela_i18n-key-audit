// Test files invent key-shaped strings; they must not count.
it("renders", () => { expect(t('totally.made.up.in.a.test')).toBeTruthy() })
