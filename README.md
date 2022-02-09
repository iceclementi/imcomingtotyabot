# I'm Coming To TYA Bot
![Current version](https://img.shields.io/badge/version-v1.1-blue)
<a href="https://github.com/python-telegram-bot/python-telegram-bot">![Python Telegram Bot version](https://img.shields.io/badge/python--telegram--bot-v13.7-teal)</a>
![Supported Python version](https://img.shields.io/badge/python-3.6%20%7C%203.7%20%7C%203.8%20%7C%203.9-teal?logo=python&logoColor=yellow)
![MIT License](https://img.shields.io/badge/license-MIT-orange)
<a href="https://t.me/imcomingtotyabot">![Bot Username](https://img.shields.io/badge/username-@imcomingtotyabot-blue?logo=telegram)</a>

_Adapted from [countmeinbot](https://github.com/whipermr5/countmeinbot) by [whipermr5](https://github.com/whipermr5/)_

---

This is a private project to build a Telegram bot which helps to build polls.
What's unique about this bot is that it allows users to **write comments** on their chosen option!

While this may be a private project, it is **open-source**. 
Feel free to use my code, make changes, and run on your own server 😉.

---

<table>
  <tbody>
    <tr align="left">
      <th><h3>ℹ What's New?</h3></th>
    </tr>
    <tr>
      <td>
        <b>Access</b>
        <ul>
          <li>Access to the bot is now restricted 😯
            <ul>
              <li>This is to prevent database from overloading from public users</li>
              <li>Request for bot access from the <b>bot admin</b></li>
            </ul>
          </li>
        </ul>
        <b>Groups</b>
        <ul>
          <li>You can now create groups* to share your created polls! 😁
            <ul>
              <li><i>Only if permission is given to you by the <b>bot admin</b></i></li>
            </ul>
          </li>
          <li>Invite group members to join your group</li>
          <li>Share and view created polls from other group members</li>
        </ul>
      </td>
    </tr>
  </tbody>
</table>

---

## Features

### Polls
- Build a standard poll with options where users can vote their names
- Toggle between single or multiple votes allowed for each user
- Toggle whether a comment is required for each option in the poll
- Users may leave a comment for an option they selected
  - If comment is required, users are forced to enter a comment or their vote will not be registered

### Groups 🆕
<table>
  <tr>
    <td><h3>⚠</h3></td>
    <td>
      Only users with permission given by the <b>bot admin</b> can create groups. 
      However, you can still join groups via group invites 😄.
    </td>
  </tr>
</table>

- Create a group and invite members to share and view each other's polls
- Group owner can remove members and group polls from the group
- Create password to secure the group

---

## Bot Usage

### Commands
<table>
  <tr>
    <td><h3>ℹ</h3></td>
    <td>
      As different users have different access privileges, the default Telegram command
      suggestions cannot be used 😭.
      <br><br>
      As a compromise, <a href="#inline-queries">inline queries</a> are used to 
      display the available commands to you. 
      <br><br>
      Alternatively, you may use the <code>/help</code> command for the bot to display 
      the list of commands available to you and their functions.
    </td>
  </tr>
</table>

Bot commands always begin with a `/` character.
Essentially it starts a conversation with the bot and triggers it to carry out a
particular action.
  
Below is a list of bot commands as of this version.

| Command         | Description                                             | Permission Type |
|:----------------|:--------------------------------------------------------|:---------------:|
| `/start`        | Views the bot's welcome message                         |      None       |
| `/poll [title]` | Builds a new poll with an optional title                |       Bot       |
| `/polls`        | Views all the polls you have built                      |       Bot       |
| `/group [name]` | Creates a new group with an optional name               |     Leader      |
| `/groups`       | Views all the groups you are in                         |       Bot       |
| `/invite`       | Sends an invite link to your friends to join your group |       Bot       |
| `/help`         | Views the help message to show available commands       |      None       |

<table>
  <tr>
    <td><h3>ℹ</h3></td>
    <td>
      If you try to use a bot command that is invalid or that you do not have access to, 
      the bot will very intelligently show you the help message instead 😆.
    </td>
  </tr>
</table>

### Inline Queries
Inline queries to the bot begin with the bot's username, i.e. `@imcomingtotyabot`. The 
best thing about inline queries is its auto-complete functionality 😁.
  
Below is a list of inline queries processed by the bot as of this version.

| Inline Query       | Description                                                                               | Permission Type |
|:-------------------|:------------------------------------------------------------------------------------------|:---------------:|
| `/`                | Views all available bot commands to you                                                   |      None       |
| `/access <code>`   | Accesses the bot's standard features via the invite code sent to you by the **bot admin** |      None       |
| `/start`           | Views the bot's welcome message                                                           |      None       |
| `/poll`            | Builds a new poll                                                                         |       Bot       |
| `/poll <title>`    | Builds a new poll with the given title                                                    |       Bot       |
| `/polls`           | Views all the polls you have built                                                        |       Bot       |
| `/polls [filter]`  | Shows polls filtered by title for you to choose to view                                   |       Bot       |
| `/group`           | Creates a new group                                                                       |     Leader      |
| `/group <name>`    | Creates a new group with the given name                                                   |     Leader      |
| `/groups`          | View all the groups you are in                                                            |       Bot       |
| `/groups [filter]` | Shows groups filtered by name for you to choose to view                                   |       Bot       |
| `/invite`          | Sends an invite link to your friends to join your group                                   |       Bot       |
| `/invite [filter]` | Shows groups filtered by name for you to choose to send an invite link for                |       Bot       |
| `/join <code>`     | Joins a group via the invite code sent by an existing group member                        |      None       |
| `/help`            | Views the help message to show available commands                                         |      None       |
| `[filter]`         | Shows a list of polls filtered by title for you to choose to publish                      |       Bot       |

<table>
  <tr>
    <td><h3>ℹ</h3></td>
    <td>
      Inline queries to the bot will automatically filter out the options that are not
      available to you.
    </td>
  </tr>
</table>

---

## Upcoming Features
- Create command to show all group polls
- Create new poll type: attendance poll
  - Input the names of all the users beforehand
  - Allocate each name to one or more options in the poll
- Enable users to create custom templates to build a poll faster! 😎

---

*Feel free to give any requests for new features or report any bugs* 🕷 *to the 
**bot admins**!* 
*Your feedback is very much appreciated!* 😊
