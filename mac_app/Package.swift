// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "CheesesHVACControlDeck",
    platforms: [.macOS(.v13)],
    products: [
        .executable(
            name: "CheesesHVACControlDeck",
            targets: ["CheesesHVACControlDeck"]
        )
    ],
    targets: [
        .executableTarget(
            name: "CheesesHVACControlDeck"
        )
    ]
)
